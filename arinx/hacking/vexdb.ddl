-- Operand types.
-- Based on `enum IRType` in `VEX/pub/libvex_ir.h`
--
-- The VEX IRType is extended here because it represents SIMD
-- registers as 'V128', 'V256', which are (from our perspective)
-- underspecified. We want to be able to reconstruct the IRType, but
-- we also want to be able to differentiate between 16x 8-bit lanes
-- and 4x 64-bit lanes and whether they're integers or floats.
--
-- We do this by having an `IRType` table that exactly reflects the
-- VEX `enum` and having an "extension" table. We "unify" these in a 

-- For SQLite:
PRAGMA foreign_keys=ON;

DROP TABLE IF EXISTS IRType;
CREATE TABLE IF NOT EXISTS IRType (
       id    INTEGER PRIMARY KEY,  -- value in IRType enum
       btype CHAR(1) NOT NULL,     -- basic type designator (e.g. 'F', 'I')
       nbits SMALLINT NOT NULL,    -- number of bits

       UNIQUE(btype,nbits)
);

-- SELECT 'Ity_' || btype || nbits FROM IRType;

DROP TABLE IF EXISTS IRTypeExt;
CREATE TABLE IF NOT EXISTS IRTypeExt (
       id     INTEGER PRIMARY KEY, -- we'll live with whatever the database decides
       parent INTEGER NOT NULL,
       nlanes TINYINT NOT NULL,    -- number of SIMD lanes (zero for a scalar)
       ltype  CHAR(1) NOT NULL,    -- lane type designator
       lwidth SMALLINT NOT NULL,   -- lane width in bits

       FOREIGN KEY(parent) REFERENCES IRType(id)
);

-- We implement a hack here to get contiguous unique IDs for the rows
-- of the view we kinda-sorta assume that IRTypeExt's IDs are
-- contiguous starting at 1, which is almost certainly going to be
-- true because of how we build the database: we don't have to worry
-- about rows being deleted and VACUUMed.
DROP VIEW IF EXISTS Ity;
CREATE VIEW IF NOT EXISTS Ity AS
  SELECT
    CASE WHEN x.id IS NULL THEN
      t.id
    ELSE
      x.id+(SELECT MAX(id) FROM IRType)
    END
  AS id,
    t.btype, t.nbits, x.nlanes, x.ltype, x.lwidth,
    CASE WHEN x.id IS NULL THEN
      'Ity_' || t.btype || t.nbits
    ELSE
      'Xty_' || x.nlanes || 'x' || x.ltype || x.lwidth 
    END
  AS cenum
  FROM IRType t LEFT OUTER JOIN IRTypeExt x
  ON x.parent = t.id
  ORDER BY id
;

-- Table of signatures
DROP TABLE IF EXISTS Sig;
CREATE TABLE IF NOT EXISTS Sig (
       id  INTEGER PRIMARY KEY,
       n_opds  TINYINT NOT NULL,           -- number of operands
       n_types TINYINT NOT NULL,           -- number of distinct types in operand list
       r_mode  BOOLEAN NOT NULL DEFAULT 0, -- indicate that 'res' is, in fact, a rounding mode
       res INTEGER NOT NULL,               -- there's always a result
       od1 INTEGER NOT NULL,               -- there's always at least one actual operand
       od2 INTEGER     NULL,               -- second and subsequent operands may not be present
       od3 INTEGER     NULL,
       od4 INTEGER     NULL,

       FOREIGN KEY(res) REFERENCES Ity(id),
       FOREIGN KEY(od1) REFERENCES Ity(id),
       FOREIGN KEY(od2) REFERENCES Ity(id),
       FOREIGN KEY(od3) REFERENCES Ity(id),
       FOREIGN KEY(od4) REFERENCES Ity(id),
       UNIQUE(res,od1,od2,od3,od4)
);

-- Human-readable view of signatures
DROP VIEW IF EXISTS SigView;
CREATE VIEW IF NOT EXISTS SigView AS
    SELECT s.id, s.n_opds, s.n_types, s.r_mode,
        res.cenum AS 'res',
        od1.cenum AS 'od1',
        od2.cenum AS 'od2',
        od3.cenum AS 'od3',
        od4.cenum AS 'od4'
    FROM Sig s
       JOIN
         Ity res, Ity od1 ON s.res=res.id AND s.od1=od1.id
       LEFT OUTER JOIN
         Ity od2 ON s.od2=od2.id
       LEFT OUTER JOIN
         Ity od3 ON s.od3=od3.id
       LEFT OUTER JOIN
         Ity od4 ON s.od4=od4.id
    ORDER BY s.id      
;      
