# Add "--keep-going" for debugging with multiple sphinx-build issues.
SPHINXOPTS    ?= -vv -W -n
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = build

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Used to publish the build documentation to the local nginx webroot
# I use "/var/www/html/minder" for this.
pushwww:
	rsync --delete -hrPvi "$(BUILDDIR)/html/" "/var/www/html/minder/"

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
