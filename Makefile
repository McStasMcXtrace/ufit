.PHONY: clean resource

SHELL=/bin/bash

RCC5 = pyrcc5

resource: resource/gui.qrc
	$(RCC5) -o ufit/guires_qt5.py $<

clean:
	rm -rf build
	find . -name '*.pyc' -print0 | xargs -0 rm -f
