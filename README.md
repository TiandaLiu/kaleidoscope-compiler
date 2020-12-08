# MPCS-51300 Compiler
## Team member
    Zhong Chu <zhongchu@uchicago.edu>
    Tianda Liu <tliu77@uchicago.edu>

## Usage
    python ekcc.py [-emit-ast -emit-llvm -jit -O] <input_file> [args]
    
    -emit-ast:  save ast to <input_file_name>.yaml
    -emit-llvm: save ir to <input_file_name>.ll
    -jit:       execute the source code directly and print results to console
    -O:         optimization mode
    [args]      pass arguments to source code
## Requirements
    Python >= 3.6
    PyYAML 5.3.1: pip install PyYAML
    ply 3.11: pip install ply
    llvmlite 0.34.0: pip install llvmlite

## References
    http://www.dabeaz.com/ply/ply.html
    https://ply.readthedocs.io/en/latest/ply.html#yacc
    https://github.com/symhom/Kaleidoscope_Compiler
    https://github.com/dabeaz/ply/tree/master/example
    https://llvmlite.readthedocs.io/en/latest/index.html
    https://blog.usejournal.com/writing-your-own-programming-language-and-compiler-with-python-a468970ae6df