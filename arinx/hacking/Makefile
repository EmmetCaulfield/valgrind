DEPS:=irtypes.lst unique-opsigs.csv irops.lst all-opsigs.csv

default: vexdb.db
#	@echo No default thing to do here

files: unique-opsigs.csv unique-opclasses.lst irops.lst irtypes.lst

src: ai_classes.c

vexdb.db: vexdb.ddl $(DEPS)
	sqlite3 $@ < vexdb.ddl
	./insert-irtypes.py
	./insert-opsigs.py
	./insert-irops.py

irtypes.lst: extract-irtypes.sh
	./extract-irtypes.sh

unique-opsigs.csv: all-opsigs.csv

irops.lst: extract-irops.sh
	./extract-irops.sh

all-opsigs.csv: extract-opsigs.sh
	./extract-opsigs.sh

all-opclasses.csv: guess-vtypes.py all-opsigs.csv
	./guess-vtypes.py

unique-opclasses.lst: all-opclasses.csv

ai_classes.c: ai_classes.py all-opclasses.csv
	./ai_classes.py

ai_classes.h: ai_classes.c

clean:
	rm -f *~ vexdb.db *.lst *.csv *.o
