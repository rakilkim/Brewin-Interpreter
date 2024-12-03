from intbase import InterpreterBase, ErrorType
from brewparse import parse_program
import copy

# if/for conditionals, arguments of standalone calls to inputi/inputs/print, raise
class Interpreter(InterpreterBase):
    class Thunk:
        cache = []
        def __init__(self, expr, snapshot):
            self.expr = expr  
            self.value = None  
            self.snapshot = copy.deepcopy(snapshot)
        def evaluate(self, interpreter):
            if self.value is None:
                for expr, val in self.cache:
                    if str(self.expr) == str(expr):
                        self.value = val
                        return self.value
                original = interpreter.vars
                interpreter.vars = self.snapshot
                self.value = interpreter.run_expr(self.expr)
                self.cache.append((self.expr, self.value))
                interpreter.vars = original
            return self.value
    
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)

        self.funcs = {} # {(name,n_args):element,}
        self.vars = [] # [({name:val,},bool),]
        self.bops = {'+', '-', '*', '/', '==', '!=', '>', '>=', '<', '<=', '||', '&&'}

    def run(self, program):
        ast = parse_program(program)
        print("")
        print(ast)
        print("")
        for func in ast.get('functions'):
            self.funcs[(func.get('name'),len(func.get('args')))] = func

        main_key = None

        for k in self.funcs:
            if k[0] == 'main':
                main_key = k
                break

        if main_key is None:
            super().error(ErrorType.NAME_ERROR, '')

        self.run_fcall(self.funcs[main_key])

    def run_vardef(self, statement):
        name = statement.get('name')

        if name in self.vars[-1][0]:
            super().error(ErrorType.NAME_ERROR, '')

        self.vars[-1][0][name] = None

    def run_assign(self, statement):
        name = statement.get('name')

        for scope_vars, is_func in self.vars[::-1]:
            if name in scope_vars:
                scope_vars[name] = self.Thunk(statement.get('expression'), self.vars)
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
                if type(c_out) == list:
                    return c_out
                if type(c_out) == bool:
                    out += str(c_out).lower()
                else:
                    out += str(c_out)

            super().output(out)

            return None
        
        if (fcall_name, len(args)) not in self.funcs:
            super().error(ErrorType.NAME_ERROR, '')

        func_def = self.funcs[(fcall_name, len(args))]

        template_args = [a.get('name') for a in func_def.get('args')]
        passed_args = [self.Thunk(a, self.vars) for a in args]

        self.vars.append(({k:v for k,v in zip(template_args, passed_args)}, True))
        res, _ = self.run_statements(func_def.get('statements'))
        self.vars.pop()

        return res

    def run_if(self, statement):
        cond = self.run_expr(statement.get('condition'))

        if type(cond) != bool:
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

            if type(cond) != bool:
                super().error(ErrorType.TYPE_ERROR, '')

            if ret or not cond: break

            self.vars.append(({}, False))
            res, ret = self.run_statements(statement.get('statements'))
            self.vars.pop()

            self.run_assign(statement.get('update'))

        return res, ret
    
    def run_try(self, statement):
        res, ret = None, False

        self.vars.append(({}, False))

        res, ret = self.run_statements(statement.get('statements'))

        self.vars.pop()

        catchers = statement.get('catchers')

        for catcher in catchers:
            if type(res) == list and catcher.get('exception_type') == res[0]:
                self.vars.append(({}, False))
                res, ret = self.run_statements(catcher.get('statements'))
                self.vars.pop()
                break

        return res, ret
    
    def run_raise(self, statement):
        raise_val = self.run_expr(statement.get('exception_type'))
        if type(raise_val) != str:
            super().error(ErrorType.TYPE_ERROR, '')
        return [raise_val]

    def run_return(self, statement):
        expr = statement.get('expression')
        if expr:
            return self.run_expr(expr)
        return None

    def run_statements(self, statements):
        res, ret = None, False

        for statement in statements:
            kind = statement.elem_type
            if res and not ret:
                break
            if kind == 'vardef':
                self.run_vardef(statement)
            elif kind == '=':
                self.run_assign(statement)
            elif kind == 'fcall':
                res = self.run_fcall(statement)
            elif kind == 'if':
                res, ret = self.run_if(statement)
                if ret: break
            elif kind == 'for':
                res, ret = self.run_for(statement)
                if ret: break
            elif kind == 'try':
                res, ret = self.run_try(statement)
                if ret: break
            elif kind == 'raise':
                res = self.run_raise(statement)
                break
            elif kind == 'return':
                res = self.run_return(statement)
                ret = True
                break

        return res, ret

    def run_expr(self, expr):
        kind = expr.elem_type

        if kind == 'int' or kind == 'string' or kind == 'bool':
            return expr.get('val')

        elif kind == 'var':
            var_name = expr.get('name')

            for scope_vars, is_func in self.vars[::-1]:
                if var_name in scope_vars:
                    return scope_vars[var_name].evaluate(self)

                if is_func: break

            super().error(ErrorType.NAME_ERROR, '')

        elif kind == 'fcall':
            return self.run_fcall(expr)

        elif kind in self.bops:
            l, r = self.run_expr(expr.get('op1')), self.run_expr(expr.get('op2'))
            tl, tr = type(l), type(r)
            if tl == list:
                return l
            if tr == list:
                return r
            if kind == '==': return tl == tr and l == r
            if kind == '!=': return not (tl == tr and l == r)

            if tl == str and tr == str:
                if kind == '+': return l + r

            if tl == int and tr == int:
                if kind == '+': return l + r
                if kind == '-': return l - r
                if kind == '*': return l * r
                if kind == '/': 
                    if r == 0:
                        return ["div0"]
                    return l // r
                if kind == '<': return l < r
                if kind == '<=': return l <= r
                if kind == '>': return l > r
                if kind == '>=': return l >= r
            
            if tl == bool and tr == bool:
                if kind == '&&': return l and r
                if kind == '||': return l or r

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
func divide(a, b) {
  return a / b;
}

func main() {
  try {
    var result;
    result = divide(10, 0);  /* evaluation deferred due to laziness */
    print("Result: ", result); /* evaluation occurs here */
  }
  catch "div0" {
    print("Caught division by zero!");
  }
}
	"""
    interpreter = Interpreter()
    interpreter.run(program_source)
'''
func main() {
  var result;
  result = f(3) + 10;
  print("done with call!");
  print(result);  /* evaluation of result happens here */
  print("about to print result again");
  print(result);
}

func f(x) {
  print("f is running");
  var y;
  y = 2 * x;
  print("f is about to return");
  return y;
}
'''
if __name__ == '__main__':
    main()