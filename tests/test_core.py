"""Source-only smoke checks for the MANTLE exact and mechanism layers."""

from mantle.exact.state import initial_state
from mantle.exact.value_functions import MantleExactSolver
from mantle.mechanisms.partition_refinement import refine_partition


def test_exact_solver_returns_a_policy() -> None:
    solver = MantleExactSolver(horizon=1)
    result = solver.solve((initial_state(0),))
    assert len(result.worst.to_list()) == 5
    assert solver.nodes
    assert solver.policy


def test_refined_partition_covers_every_information_node() -> None:
    solver = MantleExactSolver(horizon=1)
    solver.solve((initial_state(0),))
    partition = refine_partition(solver.information_sets, solver.edges)
    assert set(partition["class_of"]) == set(solver.information_sets)
