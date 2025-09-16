from evalidate import EvalException, Expr, base_eval_model

expression_model = base_eval_model.clone()
expression_model.nodes.append("JoinedStr")
expression_model.nodes.append("FormattedValue")


def evaluate_expression(expression: str, context: dict):
    try:
        return Expr(expression, model=expression_model).eval(context)
    except EvalException as e:
        raise ValueError(e) from e
