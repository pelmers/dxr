all:
	# Link paths in dxr.config.in to current working directory
	# replaces PWD with `pwd` and produces dxr.config
	cat dxr.config.in | sed -e 's?PWD?'`pwd`'?g' > dxr.config
	# extract the repo metadata from the archive
	cd code; tar -xf hg.tar; cd -
	# Navigate into the DXR folder, build using config file
	dxr-build.py
	# Launch the hg web view
	cd code; hg serve -p 8001 --pid-file ../hgserve.pid > /dev/null 2>/dev/null &
	# Launch test server at port 8000:
	# dxr-serve.py target
clean:
	rm -rf dxr.config
	rm -rf temp
	rm -rf target
	rm -rf code/.hg
	cat hgserve.pid | xargs kill -9
	rm -f hgserve.pid
