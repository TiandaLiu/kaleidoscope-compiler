import ply.yacc as yacc
from strings import *
from eklexer import tokens

precedence = (
  ('nonassoc', 'IF'),
  ('nonassoc', 'ELSE'),
  ('right', 'ASSIGN'),
  ('left', 'OR'),
  ('left', 'AND'),
  ('left', 'EQUAL'),
  ('left', 'LT', 'GT'),
  ('left', 'PLUS', 'MINUS'),
  ('left','TIMES','DIVIDE'),
  ('right','UOP', 'TYPECAST'),
)

# <prog> ::= ​<extern>​* ​<func>​+
def p_prog(p):
  '''prog : funcs
          | externs funcs'''
  if len(p) == 2:
    p[0] = {name: prog, funcs: p[1]}
  else:
    p[0] = {name: prog, funcs: p[2], externs: p[1]}


# <externs> ::= ​<extern>​+
def p_externs(p):
  '''externs : extern
             | extern externs'''
  if len(p) == 2:
    p[0] = {name: externs, externs:[p[1]]}
  else:
    appendToHead(p[2], externs, p[1])
    p[0] = p[2]


# <funcs> ::= ​<func>​+
def p_funcs(p):
  '''funcs : func
           | func funcs'''
  if len(p) == 2:
    p[0] = {name: funcs, funcs:[p[1]]}
  else:
    appendToHead(p[2], funcs, p[1])
    p[0] = p[2]


# <extern> ::= extern ​<type>​ ​<globid>​ "(" ​<tdecls>​? ")" ";"
def p_extern(p):
  '''extern : EXTERN TYPE globid LPAREN RPAREN SEMICOLON
            | EXTERN TYPE globid LPAREN tdecls RPAREN SEMICOLON'''
  if len(p) == 7:
    p[0] = {name: extern, ret_type: p[2], globid:p[3]}
  else:
    p[0] = {name: extern, ret_type: p[2], globid:p[3], tdecls: p[5]}


# <func> ::= def ​<type>​ ​<globid>​ "(" ​<vdecls>​? ")" ​<blk> ::= "{" ​<stmts>​? "}"
def p_func(p):
  '''func : DEF TYPE globid LPAREN RPAREN blk
          | DEF TYPE globid LPAREN vdecls RPAREN blk'''
  if len(p) == 7:
    p[0] = {name: func, ret_type: p[2], globid: p[3], blk: p[6]}
  else:
    p[0] = {name: func, ret_type: p[2], globid: p[3], vdecls: p[5], blk:p[7]}


# <blk> ::= "{" ​<stmts>​? "}"
def p_blk(p):
  '''blk : LBRACE RBRACE
         | LBRACE stmts RBRACE'''
  if len(p) == 3:
    p[0] = {name: blk}
  else:
    p[0] = {name: blk, contents: p[2]}


# <stmts> ::= ​<stmt>​+
def p_statements(p):
  '''stmts : stmt
           | stmt stmts'''
  if len(p) == 2:
    p[0] = {name: stmts, stmts: [p[1]]}
  else :
    appendToHead(p[2], stmts, p[1])
    p[0] = p[2]


# stmt ::= ​<blk>
#       | return ​<exp>​? ";"
#       | ​<vdecl>​ "=" ​<exp>​ ";"
#       | ​<exp>​ ";"
#       | while "(" ​<exp>​ ")" ​<stmt>
#       | if "(" ​<exp>​ ")" ​<stmt>​ (else ​<stmt>​)? 
#       | print ​<exp>​ ";"
#       | print ​<slit>​ ";"
def p_blkStmt(p):
  '''stmt : blk'''
  p[0] = {name: blk, contents: p[1]}

def p_return(p):
  '''stmt : RETURN SEMICOLON
          | RETURN exp SEMICOLON'''
  if len(p) == 4:
    p[0] = {name: ret, exp: p[2]}
  else:
    p[0] = {name: ret}

def p_vdeclStmt(p):
  '''stmt : vdecl ASSIGN exp SEMICOLON'''
  p[0] = {name: vardeclstmt, vdecl: p[1], exp: p[3]}

def p_expSemi(p):
  '''stmt : exp SEMICOLON'''
  p[0] = {name: expstmt, exp: p[1]}

def p_while(p):
   '''stmt : WHILE LPAREN exp RPAREN stmt'''
   p[0] = {name: whileStmt, cond: p[3], stmt: p[5]}

def p_if(p):
  '''stmt : IF LPAREN exp RPAREN stmt %prec IF
          | IF LPAREN exp RPAREN stmt ELSE stmt'''
  if len(p) == 6:
    p[0] = {name: ifStmt, cond: p[3], stmt: p[5]}
  else:
    p[0] = {name: ifStmt, cond: p[3], stmt: p[5], else_stmt: p[7]}

def p_printExp(p):
  '''stmt : PRINT exp SEMICOLON'''
  p[0] = {name : printStmt, exp : p[2]}

def p_printSlit(p):
  '''stmt : PRINT slit SEMICOLON'''
  p[0] = {name: "printslit", string: p[2]}


# <exps> ::= ​<exp>​ | ​<exp>​ "," ​<exps>
def p_exps(p):
  ''' exps : exp
           | exp COMMA exps'''
  if len(p) == 2:
    p[0] = {name: "exps", exps: [p[1]]}
  else:
    appendToHead(p[3], exps, p[1])
    p[0] = p[3]


# <exp> ::= "(" ​<exp>​ ")"
#       | ​<binop>
#       | ​<uop>
#       | ​<lit>
#       | ​<varid>
#       | ​<globid>​ "(" ​<exps>​? ")"
def p_expParen(p):
  '''exp : LPAREN exp RPAREN'''
  p[0] = p[2]

def p_expBinOpUop(p):
  '''exp : binop
         | uop'''
  p[0] = p[1]

def p_expLit(p):
  '''exp : lit'''
  if 'false' in str(p[1]) or 'true' in str(p[1]):
    p[0] = {name: "lit", typ: 'bool', value: p[1]}
  elif '.' in str(p[1]):
    p[0] = {name: "flit", typ: 'float', value: p[1]}
  else:
    p[0] = {name: "lit", typ: 'int', value: p[1]}

def p_expVarid(p):
  '''exp : varid'''
  p[0] = {name: varExp, var: p[1]}

def p_expGlobid(p):
  '''exp : globid LPAREN RPAREN
         | globid LPAREN exps RPAREN'''
  if len(p) == 4:
    p[0] = {name: funcCallExp, globid: p[1]}
  else:
    p[0] = {name: funcCallExp, globid: p[1], params: p[3]}


# <binop> ::= <arith-ops>
#         | <logic-ops>
#         | ​<varid>​ = ​<exp>​       # assignment
#         | "[" ​<type>​ "]" ​<exp> ​ # explicit type-cast
def p_binop(p):
  '''binop : arithOps
           | logicOps
           | varid ASSIGN exp
           | LBRACKET TYPE RBRACKET exp %prec TYPECAST'''
  if len(p) == 2:
    p[0] = p[1]
  elif len(p) == 4:
    p[0] = {"name": assign, "var": p[1], "exp": p[3]}
  else:
    p[0] = {"name": caststmt, "type": p[2], "exp": p[4]}


# <arith-ops> ::= ​<exp>​ * ​<exp>
#             | ​<exp>​ / ​<exp>
#             | ​<exp>​ + ​<exp>
#             | ​<exp>​ - ​<exp>
def p_arithOps(p):
  '''arithOps : exp TIMES exp
              | exp DIVIDE exp
              | exp PLUS exp
              | exp MINUS exp'''
  if p[2] == '*':
    p[0] = {"name": binop, "lhs": p[1], "op": 'mul', "rhs": p[3]}
  elif p[2] == '/':
    p[0] = {"name": binop, "lhs": p[1], "op": 'div', "rhs": p[3]}
  elif p[2] == '+':
    p[0] = {"name": binop, "lhs": p[1], "op": 'add', "rhs": p[3]}
  else:
    p[0] = {"name": binop, "lhs": p[1], "op": 'sub', "rhs": p[3]}


# <logic-ops> ::= ​<exp>​ == ​<exp>​  # equality
#             | ​<exp>​ <​ <exp>
#             | ​<exp>​ > ​<exp>
#             | ​<exp>​ && ​<exp>​    # bitwise AND only for bools
#             | ​<exp>​ || ​<exp>​    # bitwise OR only for bools
def p_logicOps(p):
  '''logicOps : exp EQUAL exp
              | exp LT exp
              | exp GT exp
              | exp AND exp
              | exp OR exp'''
  if p[2] == '==':
    p[0] = {"name": binop, "lhs": p[1], "op": 'eq', "rhs": p[3]}
  elif p[2] == '<':
    p[0] = {"name": binop, "lhs": p[1], "op": 'lt', "rhs": p[3]}
  elif p[2] == '>':
    p[0] = {"name": binop, "lhs": p[1], "op": 'gt', "rhs": p[3]}
  elif p[2] == '&&':
    p[0] = {"name": binop, "lhs": p[1], "op": 'and', "rhs": p[3]}
  else:
    p[0] = {"name": binop, "lhs": p[1], "op": 'or', "rhs": p[3]}


# <uop> ::= ! ​<exp>​  # bitwise negation on bools
#       | - ​<exp>    ​# signed negation 
def p_uop(p):
  '''uop : MINUS exp %prec UOP
         | NOT exp %prec UOP'''
  if p[1] == "-":
    p[0] = {"name" : uop, op: "minus", "exp": p[2] }
  else:
    p[0] = {"name" : uop, op: "not", "exp": p[2]}


# <lit> ::= true 
#       | false
#       | [0-9]+(\.[0-9]+)?
def p_lit(p):
  '''lit : TRUE
         | FALSE
         | LIT'''
  p[0] = p[1]


# <slit> ::= "[^"\n\r]*"
def p_slit(p):
  '''slit : SLIT'''
  p[0] = p[1]


# # no need for <ident> ::= [a-zA-Z_]+[a-zA-Z0-9_]*
# def p_id(p):
#   pass


# <varid> ::= $​<ident>   # no space between $ and <ident>
def p_varid(p):
  '''varid : VARID'''
  p[0] = p[1]


# <globid> ::= ​<ident>
def p_globid(p):
  '''globid : ID'''
  p[0] = p[1]


# <type> ::= int | cint | float | bool | void | (noalias)? ref ​<type>
def p_type(p):
  '''TYPE : INT
          | CINT
          | FLOAT
          | BOOL
          | VOID
          | REF TYPE
          | NOALIAS REF TYPE'''
  if len(p) == 2:
    p[0] = p[1]
  elif len(p) == 3:
    p[0] = "ref " + p[2]
  else:
    p[0] = "noalias ref " + p[3]


# <vdecls> ::= ​<vdecl>​ | ​<vdecl>​ "," ​<vdecls>
def p_vdecls(p):
  '''vdecls : vdecl
            | vdecl COMMA vdecls'''
  if len(p) == 2:
    p[0] = {name: vdecls, vars: [p[1]]}
  else:
    appendToHead(p[3], vars, p[1])
    p[0] = p[3]


# <tdecls> ::= ​<type>​ | ​<type>​ "," ​<tdecls>
def p_tdecls(p):
  '''tdecls : TYPE
            | TYPE COMMA tdecls'''
  if len(p) == 2:
    p[0] = {name: tdecls, 'types': [p[1]]}
  else :
    appendToHead(p[3], 'types', p[1])
    p[0] = p[3]


# <vdecl> ::= ​<type>​ ​<varid>
def p_vdecl(p):
  '''vdecl : TYPE varid'''
  p[0] = {node: vdecl, typ: p[1], var: p[2]}


# Error
def p_error(p):
    print("error: Syntax error in input!")


# Helper functions
def appendToHead(dic, key, value):
  ''' append value to the head of dic[key] '''
  dic[key].insert(0, value)
  return dic

def getAst(code):
  ''' Build the parser and generate ast '''
  yacc.yacc()
  ast = yacc.parse(code, debug=False)
  return ast
