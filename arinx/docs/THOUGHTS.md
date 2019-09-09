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
    #define AI_U (0x01) // Unsigned integer
    #define AI_S (0x02) // Signed integer
    #define AI_F (0x03) // IEEE (or similar) floating-point number
    #define AI_D (0x04) // Decimal floating-point number
    #define AI_V (0x04) // Vector

    // Three bits represent the SIMD multiplicity of operand/result:
    #define AI_0x (0x00) // Scalar (non-SIMD) operation
    #define AI_1x (0x01) // Scalar operand in SIMD register (e.g. splats & horizontals)
    #define AI_2x (0x01) // 2x operations
    #define AI_2x (0x02) // 4x operations
    #define AI_2x (0x03) // 8x operations
    #define AI_2x (0x04) // 16x operations
    #define AI_2x (0x05) // 32x operations
    #define AI_2x (0x06) // 64x operations (e.g. AVX 512 on bytes)


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

However, the 182 different signatures treat vector registers as all
having the same type (`Ity_V128` or `Ity_V256`) and don't distinguish
between, say, a `Ity_V128` that contains 16 characters and a
`Ity_V128` that contains four `float`s or two ` doubles`. For our
purposes, we _need_ this distinction, which is informally encoded into
`enum IROp` in the names of the members, e.g. `Iop_Add8x32`,
`Iop_Add64x4`, and `Iop_Mul64Fx4`, which all have `Ity_V256` operands.
