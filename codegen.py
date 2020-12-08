import strings
import copy
from ctypes import CFUNCTYPE, c_int, c_float
from llvmlite import ir
import llvmlite.binding as llvm


# declare types
i1 = ir.IntType(1)
i32 = ir.IntType(32)
f32 = ir.FloatType()


# main function
def generate_ir(ast, *args):
    '''
    Given ast, generate llvm ir by traversing the ast
    Return module
    '''
    module = initialize()
    process(ast, module, *args)
    return module

def initialize():
    '''
    Initalize llvm and module
    Return module
    '''
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()

    module = ir.Module(name="prog")
    module.triple = llvm.get_default_triple()
    return module

def declare_print_function(module, known_funcs):
    '''
    Declare printf function
    Code adapted from https://blog.usejournal.com/writing-your-own-programming-language-and-compiler-with-python-a468970ae6df
    '''
    voidptr_ty = ir.IntType(8).as_pointer()
    fnty = ir.FunctionType(ir.IntType(32), [voidptr_ty], var_arg=True)
    printf = ir.Function(module, fnty, name="printf")
    known_funcs["printf"] = "slit"
    
def process(ast, module, *sysArgs):
    if strings.externs in ast:
        process_externs(ast[strings.externs], module, *sysArgs)
    known_funcs = ast["funcList"]
    declare_print_function(module, known_funcs)
    process_funcs(ast[strings.funcs], module, known_funcs)

def process_externs(ast, module, *sysArgs):
    externList = ast[strings.externs]
    for extern in externList:
        process_extern(extern, module, *sysArgs)

def process_funcs(ast, module, known_funcs):
    funcList = ast[strings.funcs]
    for i in funcList:
        convert_func(i, module, known_funcs)

def process_extern(extern, module, *sysArgs):
    args = []
    func_name = extern["globid"]
    if "tdecls" in extern:
        for arg in extern["tdecls"]["types"]:
            args.append(ir_type(arg))
    if func_name in ["getarg", "getargf"]:
        declare_built_int_functions(module, func_name, *sysArgs)
    else:
        returnType = ir_type(extern["ret_type"])
        fnty = ir.FunctionType(returnType, args)
        func = ir.Function(module, fnty, name=func_name)

def declare_built_int_functions(module, func_name, sys_args):
    '''
    Declare getarg and getargf functions
    '''
    # parse system arguments
    ret_type = i32 if func_name == "getarg" else f32
    sys_args = list(map(float, sys_args))
    if ret_type == i32:
        sys_args = list(map(int, sys_args))
    array_type = ir.ArrayType(ret_type, len(sys_args))
    arr = ir.Constant(array_type, sys_args)

    # declare function
    fnty = ir.FunctionType(ret_type, [i32])
    func = ir.Function(module, fnty, name=func_name)

    # declare entry
    entry = func.append_basic_block("entry")
    builder = ir.IRBuilder(entry)

    #function arguments
    index = func.args[0]
    ptr_arg = builder.alloca(i32)
    builder.store(index, ptr_arg)
    value = builder.load(ptr_arg)

    # insert sys args to arr
    for index, arg in enumerate(sys_args):
        number = ir.Constant(ret_type, arg)
        builder.insert_value(arr, number, index)
    ptr = builder.alloca(array_type)
    builder.store(arr, ptr)

    int_0 = ir.Constant(i32, 0)
    address = builder.gep(ptr, [int_0,value])
    builder.ret(builder.load(address))

def convert_func(ast, module, known_funcs):
    func_name = ast[strings.globid]
    symbols = {}
    symbols['cint'] = set()
    symbols[strings.cint_args] = {}
    symbols[strings.cint_args][func_name] = []

    returnType = ir_type(ast[strings.ret_type])
    
    # add arguments to list, check noalias attributes
    if strings.vdecls in ast:
        argument_types, argument_names, is_noalias = parse_vdecls(ast[strings.vdecls], symbols, func_name)
    else:
        argument_types, argument_names, is_noalias = [], [], []
    
    # declare function
    fnty = ir.FunctionType(returnType, argument_types)
    func = ir.Function(module, fnty, name=func_name)
    known_funcs[func_name] = (fnty, symbols[strings.cint_args][func_name])

    # add entry
    entry = func.append_basic_block('entry')
    builder = ir.IRBuilder(entry)

    # add parameter info
    known_funcs[func_name] = (fnty, symbols[strings.cint_args][func_name])

    # populate known funcs
    for name, t in known_funcs.items():
        symbols[name] = t[0]
        symbols[strings.cint_args][name] = t[1]

    # go through arguments
    for index, argument in enumerate(func.args):
        if is_noalias[index]:
            argument.add_attribute('noalias')
        var_name = argument_names[index]
        var_type = argument_types[index]

        if var_type.is_pointer:
            ptr = argument
            symbols[var_name] = ptr
        else:
            ptr = builder.alloca(var_type)
            symbols[var_name] = ptr
            builder.store(argument, ptr)
    
    returned = blk(ast[strings.blk], builder, symbols)
    if ast[strings.ret_type] == 'void':
        builder.ret_void()
        return fnty
    if not returned:
        raise RuntimeError("function missing return statement")

def parse_vdecls(ast, symbols, func_name):
    type_list, name_list, is_noalias = [], [], []

    for var in ast["vars"]:
        if "cint" in var[strings.typ]:
            symbols["cint"].add(var["var"])
            symbols[strings.cint_args][func_name].append(True)
        else:
            symbols[strings.cint_args][func_name].append(False)
        type_list.append(ir_type(var["type"]))
        name_list.append(var["var"])
        is_noalias.append("noalias" in var["type"])

    return [type_list, name_list, is_noalias]

def blk(ast, builder, symbols):
    if strings.contents not in ast:
        return False
    
    legacy = copy.copy(symbols)
    for statement in ast[strings.contents][strings.stmts]:
        if stmt(statement, builder, legacy):
            return True
    return False

def stmt(ast, builder, symbols):
    name = ast["name"]
    
    if name == 'ret':
        return return_stmt(ast, builder, symbols)
    elif name == 'expstmt':
        expression(ast[strings.exp], symbols, builder)
        return False
    elif name == 'if':
        return if_stmt(ast, builder, symbols)
    elif name == 'while':
        while_stmt(ast, builder, symbols)
        return False
    elif name == 'blk':
        return blk(ast[strings.contents], builder, symbols)
    elif name == 'print':
        print_number(ast, builder, symbols)
    elif name == 'printslit':
        print_slit(ast, builder, symbols)
        return False
    elif name == 'vardeclstmt':
        vardeclstmt(ast, builder, symbols)
        return False
    else:
        raise RuntimeError('error: ast is not processed: ' + str(ast))

def return_stmt(ast, builder, symbols):
    if "exp" not in ast:
        builder.ret_void()
        return True
    
    ret_exp = expression(ast["exp"], symbols, builder)
    ret_exp = get_value(ret_exp, builder)
    builder.ret(ret_exp)
    return True

def print_number(ast, builder, symbols):
    '''
    print i1, i32, f32
    note: the floar need to be converted to double when using printf
    '''
    value = expression(ast["exp"], symbols, builder)
    value = get_value(value, builder)
    if value.type == i1:
        value = builder.zext(value, i32)
    if value.type == f32:
        value = builder.fpext(value, ir.DoubleType())
    voidptr_ty = ir.IntType(8).as_pointer()
    fmt = "%i \n\0" if value.type == i32 else "%f \n\0"
    c_fmt = ir.Constant(ir.ArrayType(ir.IntType(8), len(fmt)), bytearray(fmt.encode("utf8")))
    global_fmt = get_global_format(builder, str(value.type), c_fmt)
    fmt_arg = builder.bitcast(global_fmt, voidptr_ty)
    fn = builder.module.globals.get('printf')
    builder.call(fn, [fmt_arg, value])

def print_slit(ast, builder, symbols):
    '''
    print string with printf
    note: string need 
    '''
    string = ast['string']
    if len(string) == 0:
        return None
    voidptr_ty = ir.IntType(8).as_pointer()
    fmt = string + " \n\0"
    c_fmt = ir.Constant(ir.ArrayType(ir.IntType(8), len(fmt)), bytearray(fmt.encode("utf8")))
    global_fmt = get_global_format(builder, string, c_fmt)
    fmt_arg = builder.bitcast(global_fmt, voidptr_ty)
    fn = builder.module.globals.get('printf')
    builder.call(fn, [fmt_arg])

def get_global_format(builder, name, value):
    if name in builder.module.globals:
        return builder.module.globals[name]
    else:
        # code from https://blog.usejournal.com/writing-your-own-programming-language-and-compiler-with-python-a468970ae6df
        glob = ir.GlobalVariable(builder.module, value.type, name = name)
        glob.linkage = 'internal'
        glob.global_constant = True
        glob.initializer = value
        return glob

def while_stmt(ast, builder, symbols):
    # init
    w_body_block = builder.append_basic_block("while_body")
    w_after_block = builder.append_basic_block("while_end")

    # begin
    cond = expression(ast[strings.cond], symbols, builder)
    builder.cbranch(cond, w_body_block, w_after_block)

    # while loop
    builder.position_at_start(w_body_block)
    stmt(ast["stmt"], builder, symbols)
    cond = expression(ast[strings.cond], symbols, builder)
    builder.cbranch(cond, w_body_block, w_after_block)

    # end
    builder.position_at_start(w_after_block)

def if_stmt(ast, builder, symbols):
    cond = expression(ast["cond"], symbols, builder)
    returned = False
    if "else_stmt" in ast:
        with builder.if_else(cond) as (then, otherwise):
            with then:
                returned_then = stmt(ast["stmt"], builder, symbols)
            with otherwise:
                returned_otherwise = stmt(ast["else_stmt"], builder, symbols)
        returned = returned_then and returned_otherwise
    else:
        with builder.if_then(cond):
            stmt(ast["stmt"], builder, symbols)
    
    if returned:
        endif = builder.block
        builder.function.blocks.remove(endif)
    return returned

def vardeclstmt(ast, builder, symbols):
    vdecl = ast[strings.vdecl]
    var_type = vdecl[strings.typ]
    var_name = vdecl[strings.var]
    if 'ref' in var_type:
        ref_var_decl(ast, builder, symbols)
        return 

    vtype = ir_type(var_type)
    ptr = builder.alloca(vtype)
    symbols[var_name] = ptr
    cint = False
    # assign value to variable
    if "cint" in ast[strings.vdecl][strings.typ]:
        cint = True
        symbols["cint"].add(var_name)
    if "exp" in ast:
        exp = ast[strings.exp]
        value = expression(exp, symbols, builder, cint = cint)
        value = get_value(value, builder)

        if vtype != value.type:
            # assign int to float
            if vtype == f32:
                value = builder.sitofp(value, f32)
            
            # assign float to int
            if vtype == i32:
                if value.type == i1:
                    value = builder.zext(value, i32)
                else:
                    value = builder.fptosi(value, i32)
    try:
        builder.store(value, ptr)
    except TypeError as err:
        raise RuntimeError('error: cannot declare variable: ' + str(ast), err)

def ref_var_decl(ast, builder, symbols):
    vdecl = ast[strings.vdecl]
    var_name = vdecl[strings.var]
    exp = ast[strings.exp]
    pointee = expression(exp, symbols, builder)
    symbols[var_name] = pointee

def expression(ast, symbols, builder, neg=False, exception=False, cint=False):
    name = ast[strings.name]
    try:
        if name == strings.uop:
            return uop(ast, symbols, builder, cint)
        if name == strings.litExp or name == "flit":
            if cint:
                limit = 2147483647
                if neg:
                    limit += 1
                if ast['value'] > limit or ast['value'] < -2147483648:
                    overflows(ast, builder)
                if exception and ast['value'] == 2147483648:
                    raise Error2147483648
            return ir.Constant(ir_type(ast[strings.typ]), ast['value'])
        elif name == 'slit':
            return ast['value']
        elif name == strings.varExp:
            name = ast[strings.var]
            try:
                return symbols[name]
            except:
                raise RuntimeError('error: cannot find variable: ' + str(ast))
        elif name == 'funccall':
            func_name = ast[strings.globid]
            fn = builder.module.globals.get(func_name)
            params = ast[strings.params]

            # prepare parameters
            if func_name == "getarg" or func_name == "getargf":
                # there is only one parameter
                parameter = expression(params["exps"][0], symbols, builder)
                parameter = get_value(parameter, builder)
                parameters = [ parameter ]
            else:
                parameters = prepare_parameters(func_name, params, symbols, builder)

            return builder.call(fn, parameters)
        elif name == strings.binop:
            target_type = ast[strings.typ]
            return binop(ast, symbols, builder, target_type, cint = cint)

        elif name == strings.assign:
            var_name = ast[strings.var]

            if var_name not in symbols:
                raise RuntimeError('error: variable name has not been declared: ' + var_name)

            ptr = symbols[var_name]

            if var_name in symbols["cint"]:
                ast[strings.typ] = "cint"

            cint = False
            if "cint" in ast["type"]:
                cint = True

            value = expression(ast[strings.exp], symbols, builder, cint = cint)
            assign_value(builder, ptr, value)
            return
        
        elif name == strings.caststmt:
            target_type = ir_type(ast[strings.typ])
            source_type = ir_type(ast[strings.exp][strings.typ])
            value = expression(ast[strings.exp], symbols, builder)
            if source_type == target_type:
                return value
            else:
                # only handled float -> int and int -> float
                if source_type == f32 and target_type == i32:
                    return builder.fptosi(value, target_type, name='fptosi')
                elif source_type == i32 and target_type == f32:
                    return builder.sitofp(value, target_type, name='fptosi')
                else:
                    # in case of need
                    pass
        else:
            raise RuntimeError('error: ast is not processed: ' + str(ast))

    except KeyError as err:
        raise RuntimeError('error converting: ' + str(ast), err)

def get_value(exp, builder):
    if exp.type.is_pointer:
        return builder.load(exp)
    return exp

def binop(ast, symbols, builder, target_type, cint = False):
    lhs = expression(ast["lhs"], symbols, builder, cint = cint)
    lhs = get_value(lhs, builder)
    rhs = expression(ast["rhs"], symbols, builder, cint = cint)
    rhs = get_value(rhs, builder)
    op = ast["op"]
    flags= ["fast"]

    try:
        if cint:
            return check_int(lhs, rhs, builder, op)
        if op == "and":
            return builder.and_(lhs, rhs, name="and", flags=())
        elif op == "or":
            return builder.or_(lhs, rhs, name="or", flags=())
        elif target_type == "float":
            if op == 'add':
                return builder.fadd(lhs, rhs, name="add", flags=flags)
            elif op == 'sub':
                return builder.fsub(lhs, rhs, name='sub', flags=flags)
            elif op == 'mul':
                return builder.fmul(lhs, rhs, name='mul', flags=flags)
            elif op == 'div':
                return builder.fdiv(lhs, rhs, name='div', flags=flags)
        elif target_type == "int":
            if op == 'add':
                return builder.add(lhs, rhs, name="add")
            elif op == 'sub':
                return builder.sub(lhs, rhs, name='sub')
            elif op == 'mul':
                return builder.mul(lhs, rhs, name='mul')
            elif op == 'div':
                return builder.sdiv(lhs, rhs, name='div')
        elif target_type == "bool":
            if "int" in ast["lhs"]["type"]:
                if op == 'eq':
                    return builder.icmp_signed('==', lhs, rhs, name="eq")
                elif op == 'lt':
                    return builder.icmp_signed('<', lhs, rhs, name="lt")
                elif op == 'gt':
                    return builder.icmp_signed('>', lhs, rhs, name="gt")
            elif "float" in ast["lhs"]["type"]:
                if op == 'eq':
                    return builder.fcmp_ordered('==', lhs, rhs, name="eq", flags=flags)
                elif op == 'lt':
                    return builder.fcmp_ordered('<', lhs, rhs, name="lt", flags=flags)
                elif op == 'gt':
                    return builder.fcmp_ordered('>', lhs, rhs, name="gt", flags=flags)
            else:
                pass
        else:
            raise RuntimeError('error: ast is not processed: ' + str(ast))
    except:
        raise RuntimeError('error: cannot processing ast: ' + str(ast))

def uop(ast, symbols, builder, cint = False):
    try:
        uop_value = expression(ast["exp"], symbols, builder, neg=True, exception=True, cint = cint)
    except Error2147483648:
        return ir.Constant(i32, -2147483648)

    uop_value = get_value(uop_value, builder)
    if ast["op"] == "minus":
        if uop_value.type == i32:
            if cint:
                is_overflow = builder.icmp_signed('==', uop_value, ir.Constant(i32, -2147483648))
                with builder.if_then(is_overflow):
                    overflows(None, builder)
            return builder.neg(uop_value, name="Minus")
        else:
            f32_0 = ir.Constant(f32, 0)
            return builder.fsub(f32_0, uop_value, name='sub', flags = ["fast"])
    else: # not
        return builder.not_(uop_value, name="logicalNeg")

def prepare_parameters(func_name, params, symbols, builder):
    if not params:
        return []
    parameters = []
    fnArgs = symbols[func_name].args
    exps = params[strings.exps]
    for i in range(len(exps)):
        param = exps[i]
        argType = fnArgs[i]
        if argType.is_pointer:
            if strings.var not in param:
                raise RuntimeError("error: no variable object passed as ref type")
            var_name = param[strings.var]
            parameters.append(
                symbols[var_name]
            )
        else:
            cint = symbols[strings.cint_args][func_name][i]
            value = expression(param, symbols, builder, cint = cint)
            value = get_value(value, builder)
            parameters.append(value)
    return parameters

def assign_value(builder, ptr, value):
    value = get_value(value, builder)
    if ptr.type.pointee == i32:
        if value.type == i1:
            value = builder.zext(value, i32)
        if value.type == f32:
            value = builder.fptosi(value, i32)
    elif ptr.type.pointee == f32:
        if value.type == i1 or value.type == i32:
            value = builder.uitofp(value, f32)
    builder.store(value, ptr)
    return

def ir_type(string):
    # convert kaleidoscope type to ir type
    if "ref" in string:
        if "int" in string:
            return ir.PointerType(i32)
        return ir.PointerType(f32)
    if "int" in string:
        return i32
    if "float" in string:
        return f32
    if "bool" in string:
        return i1
    return ir.VoidType()

def check_int(lhs, rhs, builder, op):
    result = None
    if op == 'mul':
        result = builder.smul_with_overflow(lhs, rhs, name='mul')
    elif op == 'div':
        

        l = builder.icmp_signed('==', lhs, ir.Constant(i32,-2147483648), name="eq")
        r = builder.icmp_signed('==', rhs, ir.Constant(i32,-1), name="eq")
        rIsZero = builder.icmp_signed('==', rhs, ir.Constant(i32,0), name="eq")
        cond = builder.and_(l, r, name='and')
        cond2 = builder.or_(cond, rIsZero, name='or')
        with builder.if_then(cond2):
            overflows(None, builder)
        a = builder.sdiv(lhs, rhs, name='div')
        return a

    elif op == 'add':
        result = builder.sadd_with_overflow(lhs, rhs, name="add")
    elif op == 'sub':
        result = builder.ssub_with_overflow(lhs, rhs, name='sub')
    
    if result is not None:
        is_overflow = builder.extract_value(result, 1)

        with builder.if_then(is_overflow):
            overflows(None, builder)


        return builder.extract_value(result, 0)


    if op == 'eq':
        return builder.icmp_signed('==', lhs, rhs, name="eq")
    elif op == 'lt':
        return builder.icmp_signed('<', lhs, rhs, name="lt")
    elif op == 'gt':
        return builder.icmp_signed('>', lhs, rhs, name="gt")

class Error2147483648(Exception):
    pass

def overflows(ast, builder):
    message = {"string": "Error: cint value overflowed", "name": "slit"}
    print_slit(message, builder, None)

# jit compiler
def execute(module, optimization):
    parsed_module = llvm.parse_assembly(str(module))

    if optimization:
        # initialize pass manager builder
        pmb = llvm.PassManagerBuilder()
        pmb.opt_level = 3

        # initialize function pass manager
        fpm = llvm.create_function_pass_manager(parsed_module)
        pmb.populate(fpm)

        # initialize module pass manager
        pm = llvm.ModulePassManager()
        pmb.populate(pm)

        # add optimization passes
        pm.add_constant_merge_pass()
        pm.add_dead_arg_elimination_pass()
        pm.add_function_attrs_pass()
        pm.add_function_inlining_pass(200) # threshold = 200
        pm.add_global_dce_pass()
        pm.add_global_optimizer_pass()
        pm.add_ipsccp_pass()
        pm.add_dead_code_elimination_pass()
        pm.add_cfg_simplification_pass()   
        pm.add_gvn_pass()
        pm.add_instruction_combining_pass()
        pm.add_licm_pass()
        pm.add_sccp_pass()
        pm.add_sroa_pass()
        pm.add_type_based_alias_analysis_pass()
        pm.add_basic_alias_analysis_pass()

        # run optimization passes on the module
        is_modified = pm.run(parsed_module)

        # check if the optimizations made any modification to the module
        print("Optimizations made modification to the module: ", is_modified)

    parsed_module.verify()
    target_machine = llvm.Target.from_default_triple().create_target_machine()
    engine = llvm.create_mcjit_compiler(parsed_module, target_machine)
    engine.finalize_object()
    entry = engine.get_function_address("run")
    cfunc = CFUNCTYPE(c_int)(entry)
    result = cfunc()
    print("\nexit: {}".format(result))
    return parsed_module
