import argparse
import sys
import ekparser
import utils
import semanticsChecker
import codegen

def fuzztest(source_code):
    ast = ekparser.getAst(source_code)
    if not ast:
        print('no valid ast')
        sys.exit(-1)
    semanticsChecker.check(ast)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source_file', metavar='source_file', help='input file name')
    parser.add_argument('-emit-ast', action='store_true', default=False,
                        dest='boolean_emit_ast', help='generate ast and save as yaml file')
    parser.add_argument('-emit-llvm', action='store_true', default=False,
                        dest='boolean_emit_llvm', help='generate ir')
    parser.add_argument('-jit', action='store_true', default=False,
                        dest='boolean_jit', help='generate ast')
    parser.add_argument('-O)', action='store_true', help='optimization mode',
                        dest='optimization', required=False)
    parser.add_argument('sysarg', nargs='*')
    args = parser.parse_args()

    # generate ast
    source_code = utils.read_file(args.source_file)
    ast = ekparser.getAst(source_code)

    if not ast:
        raise RuntimeError('error: no valid ast')
    
    # check semantic errors
    semanticsChecker.check(ast)

    # save ast to file
    if args.boolean_emit_ast:
        utils.emit_ast(args.source_file.rsplit('.', 1)[0] + '.ast.yaml', ast)
    
    # generate ir
    module = codegen.generate_ir(ast, args.sysarg)

    # save ir to file
    if args.boolean_emit_llvm:
        utils.emit_ir(args.source_file.rsplit('.', 1)[0] + '.ll', module)
    
    # jit compiler
    if args.boolean_jit:
        module = codegen.execute(module, args.optimization)

    sys.exit(0)

if __name__== "__main__":
    main()
