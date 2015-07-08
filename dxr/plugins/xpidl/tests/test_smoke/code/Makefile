all:
	mkdir -p obj/dist/include
	python ../../../idlparser/header.py -o obj/dist/include/nsrootidl.h --cachedir=obj base/nsrootidl.idl
	python ../../../idlparser/header.py -o obj/dist/include/nsISupports.h --cachedir=obj nsISupports.idl -Ibase
	python ../../../idlparser/header.py -o obj/dist/include/nsITableEditor.h --cachedir=obj nsITableEditor.idl -Ibase
clean:
	rm -rf obj/*
