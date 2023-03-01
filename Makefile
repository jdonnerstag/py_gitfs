.PHONY: readme
readme:
	pandoc --from=markdown --to=rst --output=README.rst README.md

.PHONY: release
release: cleandist
	readme
	python3 setup.py sdist bdist_wheel upload

.PHONY: cleandist
	rm -f dist/*.whl dist/*.tar.gz

.PHONY: cleandocs
cleandocs:
	$(MAKE) -C docs clean

.PHONY: clean
clean: cleandist cleandocs

.PHONY: test
test:
	nosetests --with-coverage --cover-erase --logging-level=ERROR --cover-package=fs_gitfs -a "!slow" tests
	rm .coverage

.PHONY: slowtest
slowtest:
	nosetests --with-coverage --cover-erase --logging-level=ERROR --cover-package=fs_gitfs tests
	rm .coverage

.PHONY: testall
testall:
	tox

.PHONY: docs
docs:
	$(MAKE) -C docs html
	python -c "import os, webbrowser; webbrowser.open('file://' + os.path.abspath('./docs/build/html/index.html'))"

.PHONY: typecheck
typecheck:
	mypy -p fs_gitfs --config setup.cfg
