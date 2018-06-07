.PHONY: clean resource

SHELL=/bin/bash

RCC4 = pyrcc4
RCC5 = pyrcc5

resource: resource/gui.qrc
	$(RCC4) -py3 -o ufit/guires_qt4.py $<
	$(RCC5)      -o ufit/guires_qt5.py $<

clean:
	rm -rf build
	find . -name '*.pyc' -print0 | xargs -0 rm -f
