"""Exécute un notebook cellule par cellule dans CE process Python (pas de
sous-processus noyau Jupyter) et réinjecte les sorties réelles (texte,
figures matplotlib) dans le fichier .ipynb. Contournement nécessaire sur
cette machine : le spawn du kernel Jupyter est bloqué par une stratégie
Windows (Smart App Control / WDAC) ; outil de dev, pas un livrable.
"""

from __future__ import annotations

import ast
import base64
import io
import sys
import traceback
from pathlib import Path

import nbformat as nbf

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def execute(path: Path) -> None:
    notebook = nbf.read(path, as_version=4)
    namespace: dict = {"__name__": "__main__"}
    exec_count = 0

    for cell in notebook.cells:
        if cell.cell_type != "code":
            continue
        exec_count += 1
        cell.outputs = []
        cell.execution_count = exec_count

        source = "\n".join(
            line for line in cell.source.splitlines() if not line.strip().startswith("%matplotlib")
        )

        tree = ast.parse(source)
        trailing_expr = None
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            trailing_expr = tree.body.pop()
            # on exécute tout sauf la dernière expression, qu'on évalue à
            # part pour récupérer sa valeur (comme le ferait IPython)
            exec_tree = ast.Module(body=tree.body, type_ignores=[])
            eval_expr = ast.Expression(body=trailing_expr.value)
            ast.fix_missing_locations(exec_tree)
            ast.fix_missing_locations(eval_expr)
        else:
            exec_tree = tree
            eval_expr = None

        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            exec(compile(exec_tree, f"<cell {exec_count}>", "exec"), namespace)
            result = None
            if eval_expr:
                result = eval(compile(eval_expr, f"<cell {exec_count}>", "eval"), namespace)
        except Exception:
            sys.stdout = old_stdout
            print(f"--- Échec cellule {exec_count} dans {path.name} ---")
            print(buf.getvalue())
            traceback.print_exc()
            raise
        finally:
            sys.stdout = old_stdout

        text = buf.getvalue()
        if text:
            cell.outputs.append(nbf.v4.new_output("stream", name="stdout", text=text))

        if result is not None:
            repr_text = result.to_string() if hasattr(result, "to_string") else repr(result)
            cell.outputs.append(
                nbf.v4.new_output(
                    "execute_result",
                    data={"text/plain": repr_text},
                    execution_count=exec_count,
                )
            )

        for fignum in plt.get_fignums():
            fig = plt.figure(fignum)
            png_buf = io.BytesIO()
            fig.savefig(png_buf, format="png", bbox_inches="tight", dpi=100)
            encoded = base64.b64encode(png_buf.getvalue()).decode("ascii")
            cell.outputs.append(nbf.v4.new_output("display_data", data={"image/png": encoded}))
        plt.close("all")

    nbf.write(notebook, path)
    print(f"Exécuté avec succès : {path}")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        execute(Path(arg))
