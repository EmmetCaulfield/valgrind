-- The objective here is to construct a database that can be used to
-- generate code (e.g. lookup tables or `enum`s) to classify VEX IROps
-- according to the number of floating-point operations that they
-- perform. If that were all we would ever want to do, of course, this
-- would be overkill, but there are opportunities for further
-- classifications that have dependencies on VEX data structures that
-- could be a royal pain to maintain manually.
--
-- The naming convention for tables is that tables that *directly*
-- reflect actual VEX stuff have the exact same name as the VEX data
-- structure that they represent:
-- 
--     `IRType` reflecting `enum IRType` in `VEX/pub/libvex_ir.h`
--     `IROp` reflecting `enum IROp` in `VEX/pub/libvex_ir.h`
-- 
-- Other tables will begin "AI" (for "arithmetic intensity"), the
-- pseudo-namespace prefix we've chosen for "arinx".
--
-- Since IRType has but two vector types (`Ity_V128` and `Ity_V256`),
-- we need to extend (at least) these with more detailed information
-- that, when used by an IROp, will allow us to infer the number of
-- FLOPs performed.
--
--     `AiType` extends `IRType` with detailed vector information
-- 
-- We further introduce the notion of an "operation signature" for
-- `IROp`s. This is a tuple of the result first, then the operands in
-- order culled from the `typeOfPrimop()` function in
-- `VEX/priv/ir_defs.c`. We will call these `OpSig`s and keep them in
-- the table `AiOpSig`.
--
-- Small note: I've tried to keep the SQL as neutral as possible, even
-- though I'm currently only intending on using SQLite3. Although a
-- SMALLINT would be adequate for the `id`s in all cases, SQLite won't
-- treat that as an alias for its rowid, so we make them integers.


-- For SQLite:
PRAGMA foreign_keys=ON;

DROP TABLE IF EXISTS IRType;
CREATE TABLE IF NOT EXISTS IRType (
       id    INTEGER  PRIMARY KEY,  -- value in IRType enum
       btype CHAR(1)  NOT NULL,     -- basic type designator (e.g. 'F', 'I')
       nbits SMALLINT NOT NULL,     -- number of bits

       UNIQUE(btype,nbits)
);

DROP VIEW IF EXISTS IRTypeView;
CREATE VIEW IF NOT EXISTS IRTypeView AS
       SELECT id, btype, nbits, 'Ity_' || btype || nbits AS cenum FROM IRType;

DROP TABLE IF EXISTS AiType;
CREATE TABLE IF NOT EXISTS AiType (
       id     INTEGER  PRIMARY KEY, -- we'll live with whatever the database decides
       parent SMALLINT NOT NULL,
       nlanes TINYINT  NOT NULL,    -- number of SIMD lanes (zero for a scalar)
       ltype  CHAR(1)  NOT NULL,    -- lane type designator
       lwidth SMALLINT NOT NULL,    -- lane width in bits

       FOREIGN KEY(parent) REFERENCES IRType(id)
);

-- Table of operation signatures, AiOpSig
DROP TABLE IF EXISTS AiOpSig;
CREATE TABLE IF NOT EXISTS AiOpSig (
       id     INTEGER  PRIMARY KEY,
       nopds  TINYINT  NOT NULL,           -- number of operands
       ntypes TINYINT  NOT NULL,           -- number of distinct types in operand list
       rmode  BOOLEAN  NOT NULL DEFAULT 0, -- indicate that 'res' is, in fact, a rounding mode
       res    SMALLINT NOT NULL,           -- there's always a result
       opd1   SMALLINT NOT NULL,           -- there's always at least one actual operand
       opd2   SMALLINT     NULL,           -- second and subsequent operands may not be present
       opd3   SMALLINT     NULL,
       opd4   SMALLINT     NULL,

       FOREIGN KEY(res)  REFERENCES Ity(id),
       FOREIGN KEY(opd1) REFERENCES Ity(id),
       FOREIGN KEY(opd2) REFERENCES Ity(id),
       FOREIGN KEY(opd3) REFERENCES Ity(id),
       FOREIGN KEY(opd4) REFERENCES Ity(id),
       UNIQUE(rmode,res,opd1,opd2,opd3,opd4)
);

-- Human-readable view of signatures
DROP VIEW IF EXISTS AiOpSigView;
CREATE VIEW IF NOT EXISTS AiOpSigView AS
    SELECT s.id, s.nopds, s.ntypes, s.rmode,
        res.cenum  AS 'res',
        opd1.cenum AS 'opd1',
        opd2.cenum AS 'opd2',
        opd3.cenum AS 'opd3',
        opd4.cenum AS 'opd4'
    FROM AiOpSig s
       JOIN
         IRTypeView res, IRTypeView opd1 ON s.res=res.id AND s.opd1=opd1.id
       LEFT OUTER JOIN
         IRTypeView opd2 ON s.opd2=opd2.id
       LEFT OUTER JOIN
         IRTypeView opd3 ON s.opd3=opd3.id
       LEFT OUTER JOIN
         IRTypeView opd4 ON s.opd4=opd4.id
    ORDER BY s.id      
;      


-- Table of VEX operations (from `enum IROp`), with additional column
-- for signature:
DROP TABLE IF EXISTS IROp;
CREATE TABLE IF NOT EXISTS IROp (
     id      INTEGER  PRIMARY KEY,
     mnem    CHAR(16) NOT NULL,     -- mnemonic part of the IROp's identifier
     aiopsig INTEGER      NULL,     -- IROp's signature in AiOpSig

     FOREIGN KEY (aiopsig) REFERENCES AiOpSig(id)
);


-- Human-readable view of IROp's with signatures
DROP VIEW IF EXISTS IROpView;
CREATE VIEW IF NOT EXISTS IROpView AS
    SELECT op.id, "Iop_" || op.mnem AS irop, op.aiopsig AS opsig,
        sig.res, sig.opd1, sig.opd2, sig.opd3, sig.opd4    
    FROM IROp op
       JOIN
           AiOpSigView sig
       ON
           op.aiopsig=sig.id
    ORDER BY op.id      
;      


