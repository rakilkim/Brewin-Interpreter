from intbase import InterpreterBase, ErrorType
from brewparse import parse_program

class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)

        self.structs = {} # {name:element,}
        self.funcs = {} # {(name,n_args,type):element,}
        self.vars = [] # [({name:[val,type],},bool),]
        self.bops = {'+', '-', '*', '/', '==', '!=', '>', '>=', '<', '<=', '||', '&&'}

    def run(self, program):
        ast = parse_program(program)
        print(ast)

        for struct in ast.get('structs'):
            self.structs[struct.get('name')] = struct

        for func in ast.get('functions'):
            self.funcs[(func.get('name'),len(func.get('args')),func.get('return_type'))] = func

        main_key = None
        for k in self.funcs:
            if k[0] == 'main':
                main_key = k
                break

        if main_key is None:
            super().error(ErrorType.NAME_ERROR, '')

        self.run_fcall(self.funcs[main_key])

    def run_vardef(self, statement):
        name, var_type = statement.get('name'), statement.get('var_type')

        if name in self.vars[-1][0]:
            super().error(ErrorType.NAME_ERROR, '')
        if var_type == 'bool':
            self.vars[-1][0][name] = [False, var_type]
        elif var_type == 'int':
            self.vars[-1][0][name] = [0, var_type]
        elif var_type == 'string':
            self.vars[-1][0][name] = ['', var_type]
        else:
            self.vars[-1][0][name] = [None, var_type]

    def find_var(self, name):
        parts = name.split('.')
        part = parts.pop(0)
        location = None
        for scope_vars, is_func in self.vars[::-1]:
            if part in scope_vars:
                if scope_vars[part][1] == 'bool' or scope_vars[part][1] == 'int' or scope_vars[part][1] == 'string':
                    super().error(ErrorType.TYPE_ERROR, '')
                if scope_vars[part][0] == None:
                    super().error(ErrorType.FAULT_ERROR, '')
                location = scope_vars[part][0]
                break
            if is_func: 
                super().error(ErrorType.NAME_ERROR, '')
        # print(location)
        # print(parts)
        # print(part)
        while parts:
            if parts[0] not in location:
                super().error(ErrorType.NAME_ERROR, '')
            if len(parts) == 1:
                return location
            part = parts.pop(0)
            location = location[part]

    def run_assign(self, statement):
        name = statement.get('name')
        if '.' in name:
            n = name.split('.')[-1]
            location = self.find_var(name)
            a = self.run_expr(statement.get('expression'))
            type_a = type(a)
            if type(a) == bool:
                type_a = 'bool'
            elif type(a) == int:
                type_a = 'int'
                if location[n][1] == 'bool':
                    a = bool(a)
                    type_a = 'bool'
            elif type(a) == str:
                type_a = 'string'
            else:
                type_a = a[1]
                a = a[0]
            if type_a != location[n][1]:
                super().error(ErrorType.TYPE_ERROR, '')
            location[n] = [a, type_a]
            return
            # parts = name.split('.')
            # part = parts.pop(0)
            # location = None
            # for scope_vars, is_func in self.vars[::-1]:
            #     if part in scope_vars:
            #         if scope_vars[part][1] == 'bool' or scope_vars[part][1] == 'int' or scope_vars[part][1] == 'string':
            #             super().error(ErrorType.TYPE_ERROR, '')
            #         if scope_vars[part][0] == None:
            #             super().error(ErrorType.FAULT_ERROR, '')
            #         location = scope_vars[part][0][0]
            #         break
            #     if is_func: 
            #         super().error(ErrorType.NAME_ERROR, '')
            # print(location)
            # print(parts)
            # print(part)
            # while parts:
            #     if parts[0] not in location:
            #         super().error(ErrorType.NAME_ERROR, '')
            #     if len(parts) == 1:
            #         a = self.run_expr(statement.get('expression'))
            #         type_a = type(a)
            #         if type(a) == bool:
            #             type_a = 'bool'
            #         elif type(a) == int:
            #             type_a = 'int'
            #         elif type(a) == str:
            #             type_a = 'string'
            #         else:
            #             type_a = a[1]
            #             a = a[0]
            #         if type_a != location[parts[0]][1]:
            #             super().error(ErrorType.TYPE_ERROR, '')
            #         location[parts[0]] = [a, type_a]
            #         return
            #     part = parts.pop(0)
            #     location = location[part]
        else:
            for scope_vars, is_func in self.vars[::-1]:
                if name in scope_vars:
                    result = self.run_expr(statement.get('expression'))
                    # if type(result) == list:
                    #     result = result[0]
                    type_a = type(result)
                    var_type = scope_vars[name][1]
                    if type(result) == bool:
                        type_a = 'bool'
                    elif type(result) == int:
                        type_a = 'int'
                        if var_type == 'bool':
                            result = bool(result)
                            type_a = 'bool'
                    elif type(result) == str:
                        type_a = 'string'
                    else:
                        if var_type != 'bool' and var_type != 'int' and var_type != 'string':
                            if result == None:
                                type_a = var_type
                            else:
                                type_a = result[1]
                                result = result[0]
                        else:
                            type_a = 'error'
                    if type_a != var_type:
                        super().error(ErrorType.TYPE_ERROR, '') 
                    scope_vars[name] = [result, var_type]
                    return

                if is_func: break

        super().error(ErrorType.NAME_ERROR, '')

    def run_fcall(self, statement):
        fcall_name, args = statement.get('name'), statement.get('args')

        if fcall_name == 'inputi' or fcall_name == 'inputs':
            if len(args) > 1:
                super().error(ErrorType.NAME_ERROR, '')

            if args:
                super().output(str(self.run_expr(args[0])))

            res = super().get_input()

            return int(res) if fcall_name == 'inputi' else res

        if fcall_name == 'print':
            out = ''

            for arg in args:
                c_out = self.run_expr(arg)
                if type(c_out) == bool:
                    out += str(c_out).lower()
                elif c_out == None or type(c_out) == list:
                    out += 'nil'
                else:
                    out += str(c_out)

            super().output(out)

            return None
        
        return_type = 0
        for func in self.funcs:
            if fcall_name == func[0] and len(args) == func[1]:
                return_type = func[2]
                break

        if return_type == 0:
            super().error(ErrorType.NAME_ERROR, '')

        func_def = self.funcs[(fcall_name, len(args), return_type)]
        passed_args = []
        for i in range(len(args)): # run all the args, and check if they match the types of the function's args
            a = self.run_expr(args[i])
            type_a = type(a)
            param_type = func_def.get('args')[i].get('var_type')
            if type(a) == bool:
                type_a = 'bool'
            elif type(a) == int:
                type_a = 'int'
                if param_type == 'bool':
                    a = bool(a)
                    type_a = 'bool'
            elif type(a) == str:
                type_a = 'string'
            else:
                if param_type != 'bool' and param_type != 'int' and param_type != 'string':
                    if a == None:
                        type_a = param_type
                    else:
                        type_a = a[1]
                        a = a[0]
                else:
                    type_a = 'error'
            if type_a != param_type:
                super().error(ErrorType.TYPE_ERROR, '') 
            passed_args.append([a, type_a])

        template_args = [a.get('name') for a in func_def.get('args')]
        #passed_args = [self.run_expr(a) for a in args]

        self.vars.append(({k:v for k,v in zip(template_args, passed_args)}, True))
        res, ret = self.run_statements(func_def.get('statements'))
        self.vars.pop()
        if return_type == 'void' and res != None:
            super().error(ErrorType.TYPE_ERROR, '')
        if res == None:
            if return_type == 'int':
                return 0
            if return_type == 'bool':
                return False
            if return_type == 'string':
                return ''
        else:
            if return_type == 'int':
                if type(res) != int:
                    super().error(ErrorType.TYPE_ERROR, '')
            elif return_type == 'bool':
                if type(res) != bool or type(res) != int:
                    super().error(ErrorType.TYPE_ERROR, '')
                
            elif return_type == 'string':
                if type(res) != str:
                    super().error(ErrorType.TYPE_ERROR, '')
            else:
                if type(res) != list or return_type != res[1]:
                    super().error(ErrorType.TYPE_ERROR, '')
        return res

    def run_if(self, statement):
        cond = self.run_expr(statement.get('condition'))

        if type(cond) != bool or type(cond) != int:
            super().error(ErrorType.TYPE_ERROR, '')

        self.vars.append(({}, False))

        res, ret = None, False

        if cond:
            res, ret = self.run_statements(statement.get('statements'))
        elif statement.get('else_statements'):
            res, ret = self.run_statements(statement.get('else_statements'))

        self.vars.pop()

        return res, ret

    def run_for(self, statement):
        res, ret = None, False

        self.run_assign(statement.get('init'))

        while True:
            cond = self.run_expr(statement.get('condition'))

            if type(cond) != bool or type(cond) != int:
                super().error(ErrorType.TYPE_ERROR, '')

            if ret or not cond: break

            self.vars.append(({}, False))
            res, ret = self.run_statements(statement.get('statements'))
            self.vars.pop()

            self.run_assign(statement.get('update'))

        return res, ret

    def run_return(self, statement):
        expr = statement.get('expression')
        if expr:
            return self.run_expr(expr)
        return None

    def run_statements(self, statements):
        res, ret = None, False

        for statement in statements:
            kind = statement.elem_type

            if kind == 'vardef':
                self.run_vardef(statement)
            elif kind == '=':
                self.run_assign(statement)
            elif kind == 'fcall':
                self.run_fcall(statement)
            elif kind == 'if':
                res, ret = self.run_if(statement)
                if ret: break
            elif kind == 'for':
                res, ret = self.run_for(statement)
                if ret: break
            elif kind == 'return':
                res = self.run_return(statement)
                ret = True
                break

        return res, ret

    def run_expr(self, expr):
        kind = expr.elem_type

        if kind == 'new':
            struct_name = expr.get('var_type')
            struct = {}
            for field in self.structs[struct_name].get('fields'):
                if field.get('var_type') == 'bool':
                    struct[field.get('name')] = [False, 'bool']
                elif field.get('var_type') == 'int':
                    struct[field.get('name')] = [0, 'int']
                elif field.get('var_type') == 'string':
                    struct[field.get('name')] = ['', 'string']
                else:
                    struct[field.get('name')] = [None, field.get('var_type')]
            return [struct, struct_name]

        if kind == 'int' or kind == 'string' or kind == 'bool':
            return expr.get('val')

        elif kind == 'var':
            var_name = expr.get('name')
            if '.' in var_name:
                return self.find_var(var_name)[var_name.split('.')[-1]][0]
            for scope_vars, is_func in self.vars[::-1]:
                if var_name in scope_vars:
                    if scope_vars[var_name][1] != 'bool' and scope_vars[var_name][1] != 'int' and scope_vars[var_name][1] != 'string':
                        return scope_vars[var_name]
                    return scope_vars[var_name][0]

                if is_func: break

            super().error(ErrorType.NAME_ERROR, '')

        elif kind == 'fcall':
            for func in self.funcs:
                if expr.get('name') == func[0] and len(expr.get('args')) == func[1]:
                    if func[2] == 'void':
                        super().error(ErrorType.TYPE_ERROR, '')
            return self.run_fcall(expr)

        elif kind in self.bops:
            l, r = self.run_expr(expr.get('op1')), self.run_expr(expr.get('op2'))
            tl, tr = type(l), type(r)
            if l == None:
                tl = None
            if r == None:
                tr = None
            

            if kind == '==': 
                print(tl, tr)
                print(l, r)
                if tl == list:
                    if l[0] != None:
                        tl = tl[1]
                    else:
                        tl = None
                        l = None
                if tr == list:
                    if r[0] != None:
                        tr = tr[1]
                    else:
                        tr = None
                        r = None
                if (tl == int or tl == bool) and (tr == int or tr == bool):
                    return l == r 
                if tl != tr:
                    super().error(ErrorType.TYPE_ERROR, '')
                return tl == tr and l == r
            if kind == '!=': 
                if tl == list:
                    if l[0] != None:
                        tl = tl[1]
                    else:
                        tl = None
                        l = None
                if tr == list:
                    if r[0] != None:
                        tr = tr[1]
                    else:
                        tr = None
                        r = None
                if (tl == int or tl == bool) and (tr == int or tr == bool):
                    return l != r 
                if tl != tr:
                    super().error(ErrorType.TYPE_ERROR, '')
                return not (tl == tr and l == r)

            if tl == str and tr == str:
                if kind == '+': return l + r

            if tl == int and tr == int:
                if kind == '+': return l + r
                if kind == '-': return l - r
                if kind == '*': return l * r
                if kind == '/': return l // r
                if kind == '<': return l < r
                if kind == '<=': return l <= r
                if kind == '>': return l > r
                if kind == '>=': return l >= r
            
            if (tl == bool or tl == int) and (tr == bool or tr == int):
                if kind == '&&': return bool(l and r)
                if kind == '||': return bool(l or r)

            super().error(ErrorType.TYPE_ERROR, '')

        elif kind == 'neg':
            o = self.run_expr(expr.get('op1'))
            if type(o) == int: return -o
            
            super().error(ErrorType.TYPE_ERROR, '')

        elif kind == '!':
            o = self.run_expr(expr.get('op1'))
            if type(o) == bool: return not o

            super().error(ErrorType.TYPE_ERROR, '')

        return None

def main():
	program_source = """
struct dog {
 bark: int;
 bite: int;
}
struct cat {
 meow: int;
 scratch: int;
}

func foo(d: dog) : dog {  /* d holds the same object reference that the koda variable holds */
  d.bark = 10;
  return d;  		/* this returns the same object reference that the koda variable holds */
}

 func main() : void {
  print("hi" == nil);

}
	"""
	interpreter = Interpreter()
	interpreter.run(program_source)
if __name__ == "__main__":
	main()