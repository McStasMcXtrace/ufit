.PHONY: clean resource

SHELL=/bin/bash

RCC = pyrcc4

resource:
	-$(RCC) -py3 -o ufit/guiresource.py resource/gui.qrc

clean:
	rm -rf build
	find . -name '*.pyc' -print0 | xargs -0 rm -f
