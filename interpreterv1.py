from brewparse import parse_program
from intbase import InterpreterBase, ErrorType

class Interpreter(InterpreterBase):
	def __init__(self, console_output=True, inp=None, trace_output=False):
		super().__init__(console_output, inp)   # call InterpreterBase's constructor
		self.variables = dict()

	def run(self, program):
		ast = parse_program(program)         # parse program into AST
		main = ast.get('functions')[0]

		if main.get('name') != 'main':
			self.main_not_found_error()
		self.run_func(main)

	def run_func(self, func_node):
		for statement in func_node.get('statements'):
			self.run_statement(statement)
	
	def run_statement(self, statement_node):
		node_type = statement_node.elem_type
		if node_type == 'vardef':
			self.do_assignment(statement_node.get('name'))
		elif node_type == '=':
			var = statement_node.get('name')
			expr = statement_node.get('expression')
			if var not in self.variables:
				self.var_not_defined_error(var)
			else:
				self.variables[var] = self.evaluate_expression(expr)
		elif node_type == 'fcall':
			func = statement_node.get('name')
			self.evaluate_expression(statement_node)
	
	def do_assignment(self, name):
		if name in self.variables:
			self.var_defined_more_than_once_error(name)
		self.variables[name] = None
	
	def evaluate_expression(self, expr):
		node_type = expr.elem_type
		if self.is_expression_node(node_type):
			if node_type == '+' or node_type == '-':
				op1 = self.evaluate_expression(expr.get('op1'))
				op2 = self.evaluate_expression(expr.get('op2'))
				if type(op1) == str or type(op2) == str:
					self.incompatible_types_error()
				if node_type == '+':
					return op1 + op2
				if node_type == '-':
					return op1 - op2
			else:   # fcall
				args = expr.get('args')
				func_name = expr.get('name')
				if func_name == 'inputi':
					if len(args) > 1:
						self.inputi_param_error()
					if args:
						super().output(args[0].get('val'))
					user_input = int(super().get_input())
					return user_input
				elif func_name == 'print':
					string_to_output = []
					for element in args:
						string_to_output.append(str(self.evaluate_expression(element)))
					super().output(''.join(string_to_output))
				else:
					self.function_not_defined_error(func_name)
		elif self.is_variable_node(node_type):
			if expr.get('name') not in self.variables:
				self.var_not_defined_error(expr.get('name'))
			return self.variables[expr.get('name')]
		elif self.is_value_node(node_type):
			return expr.get('val')

	def is_expression_node(self, node_type):
		if node_type == '+' or node_type == '-' or node_type == 'fcall':
			return True
		return False 
	def is_variable_node(self, node_type):
		if node_type == 'var':
			return True
		return False
	def is_value_node(self, node_type):
		if node_type == 'int' or node_type =='string':
			return True
		return False
	
	def main_not_found_error(self):
		super().error(
    		ErrorType.NAME_ERROR,
    		"No main() function was found",)
	def var_defined_more_than_once_error(self, var_name):
		super().error(
    		ErrorType.NAME_ERROR,
    		f"Variable {var_name} defined more than once",)
	def var_not_defined_error(self, var_name):
		super().error(
			ErrorType.NAME_ERROR, 
			f"Variable {var_name} has not been defined",)
	def function_not_defined_error(self, func_name):
		super().error(
			ErrorType.NAME_ERROR, 
			f"Function {func_name} has not been defined",)
	def incompatible_types_error(self):
		super().error(
    		ErrorType.TYPE_ERROR,
    		"Incompatible types for arithmetic operation",)
	def inputi_param_error(self):
		super().error(
			ErrorType.NAME_ERROR, 
			f"No inputi() function found that takes > 1 parameter",)
	
		
def main():
	program_source = """
	func main() {
		var user_input;
		user_input = inputi();
	}
	"""
	interpreter = Interpreter()
	interpreter.run(program_source)
if __name__ == "__main__":
	main()