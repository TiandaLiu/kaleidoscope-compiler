import argparse
import sys
import ekparser
import utils
import semanticsChecker
import codegen
from time import time
import llvmlite.binding as llvm
from ctypes import CFUNCTYPE, c_int, c_float
import matplotlib.pyplot as plt

source_file = 'test/loop_test.ek'
LEVEL = 6
TIMES = 30
compile_times = [0] * LEVEL
runtimes = [0] * LEVEL

# jit compiler
def add_passes(parsed_module, level):
    if level == 0:
        return
    pm = llvm.ModulePassManager()

    if level >= 1:
        pm.add_basic_alias_analysis_pass()

    if level >= 2:
        pm.add_licm_pass()

    if level >= 3:
        pm.add_dead_arg_elimination_pass()

    if level >= 4:
        pm.add_constant_merge_pass()

    if level >= 5:
        # pm.add_constant_merge_pass()
        # pm.add_dead_arg_elimination_pass()
        pm.add_function_attrs_pass()
        pm.add_function_inlining_pass(200) # threshold = 200
        pm.add_global_dce_pass()
        pm.add_global_optimizer_pass()
        pm.add_ipsccp_pass()
        pm.add_dead_code_elimination_pass()
        pm.add_cfg_simplification_pass()   
        pm.add_gvn_pass()
        pm.add_instruction_combining_pass()
        pm.add_sccp_pass()
        pm.add_sroa_pass()
        pm.add_type_based_alias_analysis_pass()

    pm.run(parsed_module)
    return parsed_module
    

def execute(parsed_module):
    parsed_module.verify()
    target_machine = llvm.Target.from_default_triple().create_target_machine()
    engine = llvm.create_mcjit_compiler(parsed_module, target_machine)
    engine.finalize_object()
    entry = engine.get_function_address("run")
    cfunc = CFUNCTYPE(c_int)(entry)
    result = cfunc()
    # print("\nexit: {}".format(result))


def test(level):
    parser = argparse.ArgumentParser()
    parser.add_argument('sysarg', nargs='*')
    args = parser.parse_args()

    t1 = time()
    # generate ast
    source_code = utils.read_file(source_file)
    ast = ekparser.getAst(source_code)
    if not ast:
        raise RuntimeError('error: no valid ast')
    
    # check semantic errors
    semanticsChecker.check(ast)

    # generate IR
    module = codegen.generate_ir(ast, args.sysarg)
    parsed_module = llvm.parse_assembly(str(module))

    # add passes 
    add_passes(parsed_module, level)
    t2 = time()
    compile_time = t2 - t1
 
    # jit
    t3 = time()
    execute(parsed_module)
    t4 = time()
    runtime = t4 - t3

    compile_times[level] += compile_time
    runtimes[level] += runtime

def plot(compile_times, runtimes, num_level):

    x_range = [i for i in range(num_level)]

    plt.subplot(121)
    plt.plot(x_range, compile_times)
    plt.ylabel('compile time (second)')
    plt.xlabel('optimization level')
    plt.title("Compile Time")

    plt.subplot(122)
    plt.plot(x_range, runtimes)
    plt.ylabel('runtime (second)')
    plt.xlabel('optimization level')
    plt.title("Runtime")

    plt.show()


def main():
    for _ in range(TIMES):
        for i in range(LEVEL):
            test(i)
    for i in range(LEVEL):
        compile_times[i] /= TIMES
        runtimes[i] /= TIMES
    print(compile_times)
    print(runtimes)
    plot(compile_times, runtimes, LEVEL)
    sys.exit(0)

if __name__== "__main__":
    main()