import copy

# In <vdecl> ​,the type may not be void.
def vdeclVoidCheck(ast):
    vdecls = list(find('vdecl', ast))
    for vdecl in vdecls:
        if vdecl['type'] == 'void':
            raise TypeError('error: In <vdecl>, the type may not be void.')
    
    func_vdecls = list(find('vdecls', ast))
    for vdecls in func_vdecls:
        for vdecl in vdecls['vars']:
            if vdecl['type'] == 'void':
                raise TypeError('error: In <vdecl>, the type may not be void.')
 
# In ​ ref ​ <type>​, the type may not be void or itself a reference type.
def refVoidCheck(ast):
    types = list(find('types', ast)) + list(find('ret_type', ast)) + list(find('type', ast))
    for t in types:
        if ('ref' in t and 'void' in t) or (t.count('ref') > 1):
            raise TypeError('error: In <ref type> the type may not be void or itself a reference type.')

# All functions must be declared and/or defined before they are used.
def functionOrderCheck(ast, typeOfDeclaredFunctions):
    funcs = ast['funcs']['funcs']
    if 'externs' in ast:
            for extern in ast['externs']['externs']:
                typeOfDeclaredFunctions[extern['globid']] = extern['ret_type']
    for func in funcs:
        typeOfDeclaredFunctions[func['globid']] = func['ret_type']
        globids = list(find('globid', func))
        for functionCall in globids:
            if functionCall not in typeOfDeclaredFunctions:
                raise NameError('error: Cannot find function {}'.format(functionCall))
    
    ast['funcList'] = typeOfDeclaredFunctions

# A function may not return a ref type.
def funcitonRefTypeCheck(ast):
    funcs = ast['funcs']['funcs']
    for func in funcs:
        if 'ref' in func['ret_type']:
            raise RuntimeError('error: A function may not return a ref type.')

# The initialization expression for a reference variable (including function arguments) must be a variable.
def refInitializationCheck(ast):
    stmts = list(find('stmts', ast))
    flat_list = [item for sublist in stmts for item in sublist]
    for stmt in flat_list:
        if not stmt['name'] == 'vardeclstmt':
            continue
        if not 'ref' in stmt['vdecl']['type']:
            continue
        if stmt['exp']['name'] == 'lit':
            raise RuntimeError('error: The initialization expression for a reference variable (including function arguments) must be a variable.')

# All programs must define exactly one function named “run” which returns an integer (the program exit status) and takes no arguments.
def runFunctionExistCheck(ast):
    funcs = ast['funcs']['funcs']
    numOfRunFunc = 0
    for func in funcs:
        if func['globid'] == 'run':
            if func['ret_type'] != 'int' or 'vdecls' in func:
                raise RuntimeError('error: All programs must define exactly one function named “run” which returns an integer (the program exit status) and takes no arguments.')
                return
            numOfRunFunc += 1
    if numOfRunFunc != 1:
        raise RuntimeError('error: All programs must define exactly one function named “run” which returns an integer (the program exit status) and takes no arguments.')

# For every expression, determine its type 
def addTypeToExp(ast, typeOfDeclaredFunctions):
    for func in ast['funcs']['funcs']:
        typeOfDeclaredVariable = {}
        if 'vdecls' in func:
            for vdecl in func['vdecls']['vars']:
                typeOfDeclaredVariable[vdecl['var']] = vdecl['type']
                if 'ref' in vdecl['type'] and 'noalias' in vdecl['type']:
                    typeOfDeclaredVariable[vdecl['var']] = vdecl['type'][12:]
                elif 'ref' in vdecl['type']:
                    typeOfDeclaredVariable[vdecl['var']] = vdecl['type'][4:]

        func['blk']['typeOfDeclaredVariable'] = typeOfDeclaredVariable
        blkTraversal(func['blk'], typeOfDeclaredFunctions)
    return ast


def blkTraversal(blk, typeOfDeclaredFunctions):
    typeOfDeclaredVariable = blk['typeOfDeclaredVariable']
    statements = list(find('stmts', blk))
    flat_list = [item for sublist in statements for item in sublist]
    for stmt in flat_list:
        stmtTraversal(stmt, typeOfDeclaredFunctions, typeOfDeclaredVariable)


def stmtTraversal(stmt, typeOfDeclaredFunctions, typeOfDeclaredVariable):
    if 'vdecl' in stmt:
        vdecl = stmt['vdecl']
        typeOfDeclaredVariable[vdecl['var']] = vdecl['type']
    if stmt['name'] in ['blk', 'while']:
        stmt['typeOfDeclaredVariable'] = copy.deepcopy(typeOfDeclaredVariable)
        blkTraversal(stmt, typeOfDeclaredFunctions)
    elif stmt['name'] in ['if']:
        stmt['stmt']['typeOfDeclaredVariable'] = copy.deepcopy(typeOfDeclaredVariable)
        stmtTraversal(stmt['stmt'], typeOfDeclaredFunctions, typeOfDeclaredVariable)
        if 'else_stmt' in stmt:
            stmt['else_stmt']['typeOfDeclaredVariable'] = copy.deepcopy(typeOfDeclaredVariable)
            stmtTraversal(stmt['else_stmt'], typeOfDeclaredFunctions, typeOfDeclaredVariable)

    if 'cond' in stmt:
        expTraversal(stmt['cond'], typeOfDeclaredVariable, typeOfDeclaredFunctions)
        return None
    if 'exp' not in stmt:
        return None
    expTraversal(stmt['exp'], typeOfDeclaredVariable, typeOfDeclaredFunctions)

# function arguments can be void and what not, or strings
def expTraversal(exp, knownVars, typeOfDeclaredFunctions):
    if 'type' in exp:
        if exp['name'] == "caststmt":
            expTraversal(exp['exp'], knownVars, typeOfDeclaredFunctions)
        return exp['type']

    # assignment
    if exp['name'] == 'assign':
        t = expTraversal(exp['exp'], knownVars, typeOfDeclaredFunctions)
        exp['type'] = t
        knownVars[exp['var']] = t
        return t

    # varid
    if exp['name'] == 'varval':
        if exp['var'] not in knownVars:
            raise RuntimeError('error: {} is not defined'.format(exp['var']))
        exp['type'] = knownVars[exp['var']]
        return exp['type']

    # funccall
    if exp['name'] == 'funccall':
        functionName = exp['globid']
        if functionName not in typeOfDeclaredFunctions:
            raise RuntimeError('error: All functions must be declared and/or defined before they are used.')
        exp['type'] = typeOfDeclaredFunctions[functionName]
        if 'exps' in exp['params']:
            for paramExp in exp['params']['exps']:
                expTraversal(paramExp, knownVars, typeOfDeclaredFunctions)
        return exp['type']

    # uop
    if exp['name'] == 'uop':
        exp['type'] = expTraversal(exp['exp'], knownVars, typeOfDeclaredFunctions)
        return exp['type']
    
    # binop
    if exp["name"] == "binop":
        if 'type' not in exp['lhs']:
            left = expTraversal(exp['lhs'], knownVars, typeOfDeclaredFunctions)
        if 'type' not in exp['rhs']:
            right = expTraversal(exp['rhs'], knownVars, typeOfDeclaredFunctions)
        
        if exp['lhs']['type'] != exp['rhs']['type']:
            raise RuntimeError('error: The types of a binary operator don’t match.')
        
        if exp['op'] in ['eq', 'lt', 'gt', 'and', 'or']:
            exp['type'] = 'bool'
            return exp['type']
        else:
            exp['type'] = exp['lhs']['type']
            return exp['type']



# helper function, find all items with a specific key in dictionary
def find(key, dictionary):
    if not isinstance(dictionary, dict):
        return None
    for k, v in dictionary.items():
        if k == key:
            yield v
        elif isinstance(v, dict):
            for result in find(key, v):
                yield result
        elif isinstance(v, list):
            for d in v:
                for result in find(key, d):
                    yield result

# main function
def check(ast):
    typeOfDeclaredFunctions = {}

    # semantics check
    vdeclVoidCheck(ast)
    refVoidCheck(ast)
    functionOrderCheck(ast, typeOfDeclaredFunctions)
    funcitonRefTypeCheck(ast)
    refInitializationCheck(ast)
    runFunctionExistCheck(ast)

    # add type attribute to 
    addTypeToExp(ast, typeOfDeclaredFunctions)
