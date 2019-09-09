
/*--------------------------------------------------------------------*/
/*--- arinx: a Valgrind arithmetic intensity tool.       ai_main.c ---*/
/*--------------------------------------------------------------------*/

/*
   This file is part of "ArInX", a Valgrind arithmetic intensity tool, which is
   intended to measure the arithmetic (or other operational) intensity of
   software functions and modules.

   Copyright (C) 2017-2019 Emmet Caulfield
      emmet-arinx@caulfield.info

   This program is free software; you can redistribute it and/or modify it under
   the terms of the GNU General Public License as published by the Free Software
   Foundation; either version 2 of the License, or (at your option) any later
   version.

   This program is distributed in the hope that it will be useful, but WITHOUT
   ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
   FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
   details.

   You should have received a copy of the GNU General Public License along with
   this program; if not, write to the Free Software Foundation, Inc., 59 Temple
   Place, Suite 330, Boston, MA 02111-1307, USA.

   The GNU General Public License is contained in the file COPYING.
*/

#define AI_BUGS_TO ("emmet-arinx@caulfield.info")

#include "pub_tool_basics.h"
#include "pub_tool_tooliface.h"
#include "pub_tool_libcassert.h"
#include "pub_tool_libcprint.h"
#include "pub_tool_debuginfo.h"
#include "pub_tool_libcbase.h"
#include "pub_tool_options.h"
#include "pub_tool_machine.h"     // VG_(fnptr_to_fnentry)


// Default function to be called; override with --fnname
static const HChar *clo_fnname = "main";

static Bool ai_process_cmd_line_option(const HChar* arg)
{
    if( VG_STR_CLO(arg, "--fnname", clo_fnname) ) {
    } else {
	return False;
    }

    tl_assert(clo_fnname);
    tl_assert(clo_fnname[0]);
    return True;
}


static void ai_print_usage(void)
{
    VG_(printf)(
"    --fnname=<fnname>		count calls to <name> (default 'main')\n"
    );
}


static void ai_print_debug_usage(void)
{
    VG_(printf)(
"    (none)\n"
    );
}


// Operations
#define N_OPS 7
typedef enum {
    LoadOp   = 0,
    StoreOp  = 1,
    UnOp     = 2,
    BinOp    = 3,
    TriOp    = 4,
    QuadOp   = 5,
    BranchOp = 6
} Op;

// Array of type strings from VEX/pub/libvex_ir.h
#define N_TYPES 15
static const HChar *index2str[] = {
    "I1",	// 0
    "I8",
    "I16",
    "I32",
    "I64",
    "I128",
    "F16",
    "F32",
    "F64",
    "F128",
    "D32",
    "D64",
    "D128",
    "V128",
    "V256"      // 14
};
    
static const HChar* nameOfTypeIndex( Int i ) {
    tl_assert( i >= 0  );
    tl_assert( i < N_TYPES );
    return index2str[i];
}

// Convert type constant to array index
static Int type2index( IRType ty )
{
    switch (ty) {
    case Ity_I1:      return 0;
    case Ity_I8:      return 1;
    case Ity_I16:     return 2;
    case Ity_I32:     return 3;
    case Ity_I64:     return 4;
    case Ity_I128:    return 5;
    case Ity_F16:     return 6;
    case Ity_F32:     return 7;
    case Ity_F64:     return 8;
    case Ity_F128:    return 9;
    case Ity_D32:     return 10;
    case Ity_D64:     return 11;
    case Ity_D128:    return 12;
    case Ity_V128:    return 13;
    case Ity_V256:    return 14;
    default: tl_assert(0);
    }
}

// Counts
static ULong Counts[N_OPS][N_TYPES];

// Helper called from instrumented code
static VG_REGPARM(1)
void increment_count(ULong *count)
{
    (*count)++;
}
	
// A helper that adds the instrumentation for a count
static void instrument_count(IRSB* sb, Op op, IRType ty, IRExpr* guard)
{
   IRDirty* di;
   IRExpr** argv;
   const UInt typeIx = type2index(ty);

   tl_assert(op < N_OPS);
   tl_assert(typeIx < N_TYPES);

   argv = mkIRExprVec_1( mkIRExpr_HWord( (HWord)&Counts[op][typeIx] ) );
   di = unsafeIRDirty_0_N( 1, "increment_count",
                              VG_(fnptr_to_fnentry)( &increment_count ), 
                              argv);
   if (guard) di->guard = guard;
   addStmtToIRSB( sb, IRStmt_Dirty(di) );
}


// Print counts
static void print_counts ( void )
{
   Int typeIx;
   VG_(umsg)("   Type        Loads       Stores         UnOp        BinOp        TriOp       QuadOp     BranchOp    \n");
   VG_(umsg)("   ------------------------------------------------------------------------------------------------\n");
   for (typeIx = 0; typeIx < N_TYPES; typeIx++) {
       VG_(umsg)("   %-4s %'12llu %'12llu %'12llu %'12llu %'12llu %'12llu %'12llu\n",
                 nameOfTypeIndex( typeIx ),
                 Counts[LoadOp ][typeIx],
                 Counts[StoreOp][typeIx],
                 Counts[UnOp][typeIx],
                 Counts[BinOp][typeIx],
                 Counts[TriOp][typeIx],
                 Counts[QuadOp][typeIx],
                 Counts[BranchOp][typeIx]
      );
   }
}


static void ai_post_clo_init(void)
{
    Int op, tyIx;

    for(op=0; op<N_OPS; op++) {
	for(tyIx=0; tyIx<N_TYPES; tyIx++) {
	    Counts[op][tyIx] = 0;
	}
    }
}

static
IRSB* ai_instrument ( VgCallbackClosure* closure,
                      IRSB* sbIn,
                      const VexGuestLayout* layout, 
                      const VexGuestExtents* vge,
                      const VexArchInfo* archinfo_host,
                      IRType gWordTy, IRType hWordTy )
{
    Int        i;
    IRSB      *sbOut;
    IRTypeEnv *tyenv = sbIn->tyenv;
    
    sbOut = deepCopyIRSBExceptStmts(sbIn);

    // Copy verbatim any IR preamble preceding the first IMark
    i = 0;
    while (i < sbIn->stmts_used && sbIn->stmts[i]->tag != Ist_IMark) {
	addStmtToIRSB( sbOut, sbIn->stmts[i] );
	i++;
    }
    
    for(/* continue */; i<sbIn->stmts_used; i++) {
	IRStmt *st = sbIn->stmts[i];
	if( !st || st->tag==Ist_NoOp ) continue;
        
	switch( st->tag ) {
	case Ist_NoOp:
	case Ist_AbiHint:
	case Ist_Put:
	case Ist_PutI:
	case Ist_MBE:
	case Ist_IMark:
	case Ist_Dirty:
	case Ist_Exit:
            addStmtToIRSB( sbOut, st );
            break;
	case Ist_WrTmp: {
            IRExpr *expr = st->Ist.WrTmp.data;
            IRType  type = typeOfIRExpr(sbOut->tyenv, expr);
            IROp    op = Iop_INVALID;
            
            tl_assert( type != Ity_INVALID );
            
            switch (expr->tag) {
            case Iex_Load:
                instrument_count( sbOut, LoadOp, type, NULL/*guard*/ );
                break;
            case Iex_Unop:	// Unary operation
                op = expr->Iex.Unop.op;
                instrument_count( sbOut, UnOp, type, NULL/*guard*/ );
                break;
            case Iex_Binop:     // Binary operation
                op = expr->Iex.Binop.op;
                instrument_count( sbOut, BinOp, type, NULL/*guard*/ );
                break;
            case Iex_Triop:     // Ternary operation
                op = expr->Iex.Triop.details->op;
                instrument_count( sbOut, TriOp, type, NULL/*guard*/ );
                break;
            case Iex_Qop:	// Quaternary operation
                op = expr->Iex.Qop.details->op;
                instrument_count( sbOut, QuadOp, type, NULL/*guard*/ );
                break;
            case Iex_ITE:       // If-then-else
                instrument_count( sbOut, BranchOp, type, NULL/*guard*/ );
                break;
            default:
                break;
            }
            addStmtToIRSB( sbOut, st );
            break;
	}
        case Ist_Store: {
            IRExpr* data = st->Ist.Store.data;
            IRType  type = typeOfIRExpr(tyenv, data);
            tl_assert(type != Ity_INVALID);
            instrument_count( sbOut, StoreOp, type, NULL/*guard*/ );
            addStmtToIRSB( sbOut, st );
            break;
        }
	case Ist_StoreG: {
            IRStoreG* sg   = st->Ist.StoreG.details;
            IRExpr*   data = sg->data;
            IRType    type = typeOfIRExpr(tyenv, data);
            tl_assert(type != Ity_INVALID);
            instrument_count( sbOut, StoreOp, type, sg->guard );
            addStmtToIRSB( sbOut, st );
            break;
	}
	case Ist_LoadG: {
            IRLoadG* lg       = st->Ist.LoadG.details;
            IRType   type     = Ity_INVALID; /* loaded type */
            IRType   typeWide = Ity_INVALID; /* after implicit widening */
            typeOfIRLoadGOp(lg->cvt, &typeWide, &type);
            tl_assert(type != Ity_INVALID);
	    instrument_count( sbOut, LoadOp, type, lg->guard );
            addStmtToIRSB( sbOut, st );
            break;
	}
	case Ist_CAS: { // Compare-and-Swap
            //	    Int    dataSize;
            IRType dataTy;
            IRCAS* cas = st->Ist.CAS.details;
            tl_assert(cas->addr != NULL);
            tl_assert(cas->dataLo != NULL);
            dataTy   = typeOfIRExpr(tyenv, cas->dataLo);
            
	    instrument_count( sbOut, LoadOp, dataTy, NULL/*guard*/ );
	    if (cas->dataHi != NULL) /* dcas */
		instrument_count( sbOut, LoadOp, dataTy, NULL/*guard*/ );
	    instrument_count( sbOut, StoreOp, dataTy, NULL/*guard*/ );
	    if (cas->dataHi != NULL) /* dcas */
		instrument_count( sbOut, StoreOp, dataTy, NULL/*guard*/ );
            addStmtToIRSB( sbOut, st );
            break;
	}
	case Ist_LLSC: {
	    IRType dataTy;
	    if( st->Ist.LLSC.storedata == NULL ) {
		dataTy = typeOfIRTemp(tyenv, st->Ist.LLSC.result);
		instrument_count( sbOut, LoadOp, dataTy, NULL/*guard*/ );
	    } else {
		dataTy = typeOfIRExpr(tyenv, st->Ist.LLSC.storedata);
		instrument_count( sbOut, StoreOp, dataTy, NULL/*guard*/ );
	    }
	    addStmtToIRSB( sbOut, st );
            break;
	}
	default:
	    ppIRStmt(st);
	    tl_assert(0);
	}
    }
    return sbOut;
}

static void ai_fini(Int exitcode)
{
    VG_(umsg)("\n");
    VG_(umsg)("Counts\n");
    
    print_counts();

    VG_(umsg)("\n");
    VG_(umsg)("Exit code:	%d\n", exitcode);
}

static void ai_pre_clo_init(void)
{
   VG_(details_name)            ("arinx");
   VG_(details_version)         (NULL);
   VG_(details_description)     ("a Valgrind arithmetic intensity tool");
   VG_(details_copyright_author)(
      "Copyright (C) 2017-2019, and GNU GPL'd, by Emmet Caulfield.");
   VG_(details_bug_reports_to)  (AI_BUGS_TO);

   VG_(details_avg_translation_sizeB) ( 200 );

   VG_(basic_tool_funcs)        (ai_post_clo_init,
                                 ai_instrument,
                                 ai_fini);
   VG_(needs_command_line_options)(ai_process_cmd_line_option,
                                   ai_print_usage,
                                   ai_print_debug_usage);
}

VG_DETERMINE_INTERFACE_VERSION(ai_pre_clo_init)

/*--------------------------------------------------------------------*/
/*--- end                                                          ---*/
/*--------------------------------------------------------------------*/
