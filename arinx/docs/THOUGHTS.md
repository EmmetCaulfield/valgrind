According to my count, there are currently 1097 different `Iop_` codes
in the `IROp` enum in `VEX/pub/libvex_ir.h`. Two of these are the
markers `Iop_INVALID` and `Iop_LAST`, which do not correspond to any
actual operation.

The `typeOfPrimop()` function in `VEX/priv/ir_defs.c` obliquely
categorizes these (with `#define` constructors) into 6 types:

  * `UNARY` (269,62),
  * `BINARY` (747,94),
  * `TERNARY` (66,20),
  * `QUATERNARY` (13,6),
  * `COMPARISON` (equivalent to `BINARY`), and
  * `UNARY_COMPARISON` (equivalent to `UNARY`).

The non-comparison constructors take one more argument, for the
result, than their name would suggest. The comparison constructors
implicitly return `Ity_I1` and their arguments are all of the same
type, so the `COMPARISON` constructor only takes one argument, even
though it does much the same as `BINARY`, which takes 3.

After some processing, we find that 635 ops are "uniform", operating
on, and returning, just one type; 390 use two types; and 70 use 3
types. Of these, 60 are using the pseudo-type `ity_RMode` (which we
can probably ignore). No ops use more than 3 different types.

There are 182 distinct signatures, 19 have just one type (i.e. each of
the 635 uniform ops has one of these 19 signatures), 108 have two
types, and 55 have three different types.

The complete type of an operand or result can be encoded into one byte:

    // Three bits represent size of an operand/result in bits:
    #define AI_00 (0x00)    // Zero size operand (hey, it might be useful)
    #define AI_01 (0x01)    // 1-bit operand (certain logical restriction operations)
    #define AI_08 (0x02)    // 8-bit operand
    #define AI_16 (0x03)    // 16-bit operand
    #define AI_32 (0x04)    // 32-bit operand
    #define AI_64 (0x05)    // 64-bit operand
    #define AI_64 (0x06)    // 128-bit operand
    #define AI_64 (0x07)    // 256-bit operand
    
    // Two bits represent type of an operand/result:
    #define AI_I (0x00) // General integer (signed/unsigned not specified)
    #define AI_F (0x01) // IEEE (or similar) floating-point number
    #define AI_D (0x02) // Decimal floating-point number
    #define AI_V (0x03) // Vector

    // Three bits represent the SIMD multiplicity of operand/result:
    #define AI_0x  (0x00) // Scalar (non-SIMD) operation
    #define AI_1x  (0x01) // Scalar operand in SIMD register (e.g. splats & horizontals)
    #define AI_2x  (0x02) // 2x operations
    #define AI_4x  (0x03) // 4x operations
    #define AI_8x  (0x04) // 8x operations
    #define AI_16x (0x05) // 16x operations
    #define AI_32x (0x06) // 32x operations
    #define AI_64x (0x07) // 64x operations (e.g. AVX 512 on bytes)


This enables a compact encoding for up to binary operations (two
operands and a separate result):

    union AI_op_meta {
        uint32_t code;
        struct {
            uint8_t opclass; // To be discussed
            uint8_t result;
            uint8_t op1;
            uint8_t op2;
        } code;
     }

This encoding, however, cannot represent more than two operands.

An alternative is:

    union AI_op_meta {
        uint32_t code;
        struct {
            uint8_t opclass;   // To be discussed
            uint8_t optype[2]; //
            uint8_t argi;
        } meta;
     }

With this scheme, we have two types and the bit positions in `argi`
give us the type of the operand; a ternary IROp with metadata in `m`
might have arguments:

  * result: `m.meta.optype[m.meta.argi & 1]`
  * first operand: `m.meta.optype[(m.meta.argi >> 1) & 1]`
  * second operand: `m.meta.optype[(m.meta.argi >> 2) & 1]`
  * third operand: `m.meta.optype[(m.meta.argi >> 3) & 1]`

As previously noted, there are only 10 "real" signatures with 3
different types, so we could probably live with this. The problem with
full coverage, having `optype[3]` in `meta`, is that `argi` now takes
two bits per result/operand:

  * result: `m.meta.optype[m.meta.argi & 3]`
  * first operand: `m.meta.optype[(m.meta.argi >> 2) & 3]`
  * second operand: `m.meta.optype[(m.meta.argi >> 4) & 3]`
  * third operand: `m.meta.optype[(m.meta.argi >> 6) & 3]`

To represent quaternary operations now, we need 34 bits (3x8 for the
operand types and 5x2 for the result and operand indices), and this is
before we've considered the class of operation ("arithmetic",
"logical", "bitwise", etc.)

An alternative is to use a lookup table. We only have 182 different
signatures, so a single byte can be used to characterize them.

However, these signatures treat vector registers as all having the
same type (`Ity_V128` or `Ity_V256`) and don't distinguish between,
say, a `Ity_V128` that contains 16 characters and a `Ity_V128` that
contains four `float`s or two ` doubles`. There are 37 such
_signatures_ (i.e. containing one or more `Ity_V128` or `Ity_V256`)
shared by 530 `IROp`s.

The distinction we need is partially encoded into the `IROp`s in the
names of the members of the `enum`, e.g. `Iop_Add8x32`, `Iop_Add64x4`,
and `Iop_Mul64Fx4`, which all have `Ity_V256` operands. What isn't
always clear is _which_ of the operands the name-encoded
{bits}x{lanes} refer to. Very often, the `IROp`s are uniform
(e.g. `Iop_Add8x16`'s three `Ity_V128` operands are all interpreted as
having 16 lane's of 8-bit integers) but that isn't necessarily always
the case. There are a handful of `IROp`s, such as
`Iop_F32x4_2toQ16x8`, where different `Ity_V128` operands have
different type/width structures.

Furthermore, there are 110 `IROp` identifiers with an encoded `NxM`
that _don't_ have "vector" arguments, such as `Iop_Add16x2` (with
`Ity_I32` operands) and `Iop_Add8x8` (with `Ity_I64` operands). I
guess these are (in the _x86_ case) related to the 64-bit _MMX_
instructions. There remains the question why there's a distinction
between `Ity_I128` and `Ity_V128` but none between `Ity_I64` and (the
non-existant) `Ity_V64`. If there's a 64-bit vector, shouldn't there
be a 64-bit vector type?

A 128-bit vector (`V128`) register can be (merely expanding to the
other `IRType`s):

  * 16 x `I8`
  *  8 x `I16` or `F16` (half precision)
  *  4 x `I32`, `D32` or `F32` (single precision)
  *  2 x `I64`, `D64` or `F64` (double precision)
  *  1 x `I128`, `D128` or `F128` (quad precision)
    
A 256-bit vector (`V256`) register can be:
    
  * 32 x `I8`
  * 16 x `I16` or `F16` (half precision)
  *  8 x `I32`, `D32` or `F32` (single precision)
  *  4 x `I64`, `D64` or `F64` (double precision)
  *  2 x `I128`, `D128` or `F128` (quad precision)

There are also the possibilities of `128 x I1` and `256 x I1`

We might propose the most likely (but not exhaustive) enhanced vector
`AIType`s:

32-bit (children of `Ity_I32`):

  * `Aty_V4xI8`
  * `Aty_V2xI16`

64-bit (children of `Ity_I64`):

  * `Aty_V8xI8`
  * `Aty_V4xI16`
  * `Aty_V2xI32`
  * `Aty_V2xF32`

128-bit (children of `Ity_V128`)

  * `Aty_V16xI8`
  * `Aty_V8xI16`
  * `Aty_V4xI32`
  * `Aty_V2xI64`
  * `Aty_V8xF16`
  * `Aty_V4xF32`
  * `Aty_V2xF64`

256-bit (children of `Ity_V256`):

  * `Aty_V32xI8`
  * `Aty_V16xI16`
  * `Aty_V8xI32`
  * `Aty_V4xI64`
  * `Aty_V16xF16`
  * `Aty_V8xF32`
  * `Aty_V4xF64`

`arinx/hacking/aivtypes.py` confirms this intuition.
