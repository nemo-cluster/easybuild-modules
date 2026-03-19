# bwForCluster NEMO 2 Easybuild Module Tracking System

This project collects information about available software modules from different HPC architectures (genoa, h200, rtx, mi300a, milan) using lmod and easybuild.

Architectures genoa, h200, rtx and mi300a share an identical module tree (symbolic links to genoa). The collector queries lmod only once per group.

Categories include the module path prefix in parentheses, e.g. "Libraries (lib/)".

## Progress
- [x] Project setup configured
- [x] Project structure created  
- [x] Python script for module collection developed
- [x] Web interface created
- [x] Git integration set up
- [x] Tests and documentation
- [x] MediaWiki export (generate_mediawiki.py)

The system is fully implemented and ready for use!