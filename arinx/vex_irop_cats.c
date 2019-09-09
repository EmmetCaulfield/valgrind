/*---------------------------------------------------------------*/
/*--- begin                                vex_irop_classes.h ---*/
/*---------------------------------------------------------------*/

/*
   This file is part of ArInX, an arithmetic intensity tool for
   Valgrind.

   Copyright (C) 2017-2019 Emmet Caulfield
      emmet-arinx@valgrind.net

   This program is free software; you can redistribute it and/or
   modify it under the terms of the GNU General Public License as
   published by the Free Software Foundation; either version 2 of the
   License, or (at your option) any later version.

   This program is distributed in the hope that it will be useful, but
   WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program; if not, see <http://www.gnu.org/licenses/>.

   The GNU General Public License is contained in the file COPYING.
*/



/*
 * The functions, enums, etc. in this file classify IROps. 
 *
 * A "class" in the sense of this file have nothing to do with "classes" in the
 * sense of OO/C++.
 *
 * The classification is essentially by "family" (e.g. "arithmetic", "logical",
 * "bitwise", "conversion", ...), type (int, FP, ...), and size (in bits). 
 *
 * Since the purpose of `arinx` is nominally to measure floating-point
 * arithmetic intensity, we need to be able to tell the difference between, say,
 * a scalar FP128 multiplication (one FLOP) and a 8xFP16 SIMD multiplication (8
 * FLOPS). So knowing that an IROp is "a multiplication" using 128 bit registers
 * doesn't quite cut the mustard.
 *
 * I considered a few different strategies here. One was to simply classify
 * operations by family, type, and size separately. Another was to "encode" the
 * information into a 32-bit integer.


Since
 * type and size are more really attributes of the operands, it can be pretty
 * tricky to classify some IROps simply. In particular, widening/narrowing
 * operations (what is *the* size?), conversions (FP <-> int), and some other
 * operations don't really fit.
 *

 */

#ifndef ARINX_VEX_IROP_CLASSES_H
#define ARINX_VEX_IROP_CLASSES_H

#include "pub_tool_basics.h"

IROp getOpFromExpr( IRExpr *expr ) {
   tl_assert( expr != NULL );

   switch(expr->tag) {
   case Iex_Unop:
      return expr->Iex.Unop.op;
   case Iex_Binop:
      return expr->Iex.Binop.op;
   case Iex_Triop:
      return expr->Iex.Triop.details->op;
   case Iex_Qop:
      return expr->Iex.Qop.details->op;
   }
   return Iop_INVALID;
}


typedef struct Icls_ Icls;

struct Icls_ {
   Icls_INVALID = 0x0000,
      Icls_Iar8,      // 8-bit integer arithmetic (add, sub, mul, div)
      Icls_Iar16,     // 16-bit integer arithmetic
      Icls_Iar32,     // 32-bit integer arithmetic
      Icls_Iar64,     // 64-bit integer arithmetic
      
      Icls_Bit8,      // 8-bit integer logic (and, or, xor) and bit-twiddling
      Icls_Bit16,                
      Icls_Bit32,     
      Icls_Bit64,     

      Icls_ICmp8,     // 8-bit integer comparison (eq, ne, lt, gt)
      Icls_ICmp16,
      Icls_ICmp32,
      Icls_ICmp64,

      Icls_Far16,      // Half-precision floating-point (FP16) arithmetic
      Icls_Far32,      // Single-precision floating-point (add,sub,mul,div)
      Icls_Far64,      // Double-precision floating-point (FP64)
      Icls_Far128,     // Quad-precision floating-point
      
      Icls_Fex16,      // Expensive FP16 op (e.g. log, sin, cos)
      Icls_Fex32,      // Expensive FP32 op (e.g. log, sin, cos)
      Icls_Fex64,      // Expensive FP64 op (e.g. log, sin, cos)
      Icls_Fex128,     // Expensive FP128 op (e.g. log, sin, cos)

   // It's really hard to know how to handle "conversions" here. In general, we
   // have signed and unsigned widening and narrowing conversions to/from all
   // integer sizes and also the 4 FP sizes. Ignoring the signed/unsigned
   // distinction is a no-brainer, but that still leaves a large number of
   // potential categories, e.g.
   //
   //     Icls_I8toI16, Icls_I8toI32, Icls_I8toI64, Icls_I8toI128,
   //     Icls_I8toF16, Icls_I8toF32, Icls_I8toF64, Icls_I8toF128
   //     Icls_I16toI8, Icls_I16toI32, Icls_I16toI64, Icls_I16toI128,
   //     Icls_I16toF16, Icls_I16toF32, Icls_I16toF64, Icls_I16toF128
   //     Icls_I32toI8, Icls_I32toI16, Icls_I32toI64, Icls_I32toI128,
   //     Icls_I32toF16, Icls_I32toF32, Icls_I32toF64, Icls_I32toF128
   //     Icls_I64toI8, Icls_I64toI16, Icls_I64toI32, Icls_I64toI128,
   //     Icls_I64toF16, Icls_I64toF32, Icls_I64toF64, Icls_I64toF128
   //     Icls_I128toI8, Icls_I128toI16, Icls_I128toI32, Icls_I128toI64,
   //     Icls_I128toF16, Icls_I128toF32, Icls_I128toF64, Icls_I128toF128
   //     Icls_F16toI8, Icls_F16toI16, Icls_F16toI32, Icls_F16toI64,
   //     Icls_F16toI128, Icls_F16toF32, Icls_F16toF64, Icls_F16toF128
   //     Icls_F32toI8, Icls_F32toI16, Icls_F32toI32, Icls_F32toI64,
   //     Icls_F32toI128, Icls_F32toF16, Icls_F32toF64, Icls_F32toF128
   //     Icls_F64toI8, Icls_F64toI16, Icls_F64toI32, Icls_F64toI64,
   //     Icls_F64toI128, Icls_F64toF16, Icls_F64toF32, Icls_F64toF128
   //     Icls_F128toI8, Icls_F128toI16, Icls_F128toI32, Icls_F128toI64,
   //     Icls_F128toI128, Icls_F128toF16, Icls_F128toF32, Icls_F128toF64
   //
   // So, since I'm mostly interested in floating-point, I'm going to lump all
   // integer-to-integer conversions into one category:
      Icls_ICvt,        // Integer-to-integer conversion of any kind
   // And I'm going to treat the floating-point conversions as follows:
      Icls_FFCvt32W,    // A float-to-float widening conversion to FP32
      Icls_FFCvt64W,    // ... to FP64
      Icls_FFCvt128W,   // ... to FP128 
      Icls_FFCvt16N,    // A float-to-float narrowing conversion to FP16
      Icls_FFCvt32N,    // ... to FP32
      Icls_FFCvt64N,    // ... to FP64
   // And I'm going to treat integer-to-float and float-to-int conversions
   // according to the floating-point size only:
      Icls_FICvt16,     // An FP16 to any size int
      Icls_FICvt32,     // ... an FP32
      Icls_FICvt64,
      Icls_FICvt128,
      Icls_IFCvt16,     // An int of any size to FP16
      Icls_IFCvt32,     // ... to FP32
      Icls_IFCvt64,
      Icls_IFCvt128,
      
      


}



   
Icls getIcls(IRop op) {
   switch(op) {
