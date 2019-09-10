DEPS:=irtypes.lst unique-opsigs.csv irops.lst all-opsigs.csv

default: vexdb.db
#	@echo No default thing to do here

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

vtypes.csv: all-opsigs.csv
	./guess-vtypes.py

unique-vtypes.lst: guess-vtypes.py
	./guess-vtypes.py


clean:
	rm -f *~ vexdb.db *.lst *.csv
