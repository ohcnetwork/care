import ast


class VariableExtractor(ast.NodeVisitor):
    def __init__(self):
        self.variables = set()

    def visit_Call(self, node):
        for arg in node.args:
            self.visit(arg)
        for keyword in node.keywords:
            self.visit(keyword)

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store | ast.Load)):
            self.variables.add(node.id)

    def visit_Attribute(self, node):
        path = self._resolve_path(node)
        if path is not None:
            self.variables.add(path)
        else:
            self.generic_visit(node)

    def visit_Subscript(self, node):
        path = self._resolve_path(node)
        if path is not None:
            self.variables.add(path)
        else:
            self.generic_visit(node)

    def _resolve_path(self, node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            base = self._resolve_path(node.value)
            if base is None:
                return None
            return f"{base}.{node.attr}"
        if isinstance(node, ast.Subscript):
            base = self._resolve_path(node.value)
            key = self._constant_key(node.slice)
            if base is None or key is None:
                return None
            return f"{base}.{key}"
        return None

    def _constant_key(self, slice_node):
        if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
            return slice_node.value
        return None


def get_all_variables(source_code):
    tree = ast.parse(source_code.strip())
    extractor = VariableExtractor()
    extractor.visit(tree)
    return extractor.variables
