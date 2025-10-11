import math
import collections

from chemistry_data import ChemicalEquation

def _gcd(a, b):
    return math.gcd(a, b)


def _simplify_coefficients(eq):
    coefficients = [c.coefficient for c in eq.reactants] + [c.coefficient for c in eq.products]

    if not coefficients or all(c <= 0 for c in coefficients):
        return

    non_zero_coeffs = [c for c in coefficients if c > 0]
    if not non_zero_coeffs:
        return

    common_divisor = non_zero_coeffs[0]
    for coeff in non_zero_coeffs[1:]:
        common_divisor = _gcd(common_divisor, coeff)

    if common_divisor > 1:
        for comp in eq.reactants:
            comp.coefficient //= common_divisor
        for comp in eq.products:
            comp.coefficient //= common_divisor

def _apply_balancing_rule(eq):
    left_totals, right_totals, all_elements = eq.get_element_totals()

    max_diff = 0
    unbalanced_element = None

    for element in sorted(list(all_elements)):
        diff = abs(left_totals.get(element, 0) - right_totals.get(element, 0))
        if diff > max_diff:
            max_diff = diff
            unbalanced_element = element

    if max_diff == 0:
        return None

    target_compound = None
    is_reactant_side = left_totals.get(unbalanced_element, 0) < right_totals.get(unbalanced_element, 0)
    compounds_to_check = eq.reactants if is_reactant_side else eq.products

    for comp in compounds_to_check:
        if unbalanced_element in comp.elements:
            target_compound = comp
            break

    if target_compound is None:
        return None

    count_in_target = target_compound.elements.get(unbalanced_element, 0)
    required_total = right_totals.get(unbalanced_element, 0) if is_reactant_side else left_totals.get(
        unbalanced_element, 0)

    if count_in_target == 0:
        return target_compound, unbalanced_element, target_compound.coefficient + 1

    other_total = 0
    for comp in compounds_to_check:
        if comp != target_compound:
            other_total += comp.coefficient * comp.elements.get(unbalanced_element, 0)

    needed_from_target = required_total - other_total

    if needed_from_target <= 0:
        new_coefficient = target_compound.coefficient + 1
        return target_compound, unbalanced_element, new_coefficient

    if needed_from_target % count_in_target == 0:
        new_coefficient = needed_from_target // count_in_target
        if new_coefficient > target_compound.coefficient:
            return target_compound, unbalanced_element, new_coefficient

    return target_compound, unbalanced_element, target_compound.coefficient + 1


def _get_unbalanced_details(eq):
    left_totals, right_totals, all_elements = eq.get_element_totals()
    unbalanced_list = []

    for element in sorted(list(all_elements)):
        left = left_totals.get(element, 0)
        right = right_totals.get(element, 0)
        if left != right:
            unbalanced_list.append({
                "element": element,
                "left_count": left,
                "right_count": right,
                "difference": abs(left - right)
            })
    return unbalanced_list


def balance_equation(equation_str: str, max_iterations: int = 50) -> dict:
    try:
        parts = [p.strip() for p in equation_str.split('->')]
        if len(parts) != 2:
            raise ValueError("Chuỗi phương trình không hợp lệ. Phải có '->'.")

        reactants_str, products_str = parts[0], parts[1]
        reactants = [r.strip() for r in reactants_str.split('+') if r.strip()]
        products = [p.strip() for p in products_str.split('+') if p.strip()]

        if not reactants or not products:
            raise ValueError("Thiếu chất tham gia hoặc chất sản phẩm.")

        known = ChemicalEquation(reactants, products)

    except Exception as e:
        return {"success": False, "error_message": f"Lỗi phân tích cú pháp: {e}"}

    iteration_count = 0
    history = []

    while not known.is_balanced() and iteration_count < max_iterations:
        iteration_count += 1

        result = _apply_balancing_rule(known)

        step_details = {
            "step": iteration_count,
            "equation_before": str(known),
            "action": None
        }

        if result:
            target_compound, unbalanced_element, new_coefficient = result

            step_details["action"] = (
                f"Cân bằng '{target_compound.name}' để cân bằng nguyên tố '{unbalanced_element}' "
                f"(Hệ số mới: {new_coefficient})"
            )

            target_compound.coefficient = new_coefficient
        else:
            step_details["action"] = "Không tìm thấy nguyên tố mất cân bằng để tác động."
            break

        step_details["equation_after"] = str(known)
        history.append(step_details)

    if known.is_balanced():

        equation_before_simplify = str(known)

        _simplify_coefficients(known)

        equation_after_simplify = str(known)

        if equation_before_simplify != equation_after_simplify:
            iteration_count += 1
            history.append({
                "step": iteration_count,
                "equation_before": equation_before_simplify,
                "action": "Rút gọn các hệ số về tỷ lệ số nguyên tối thiểu.",
                "equation_after": equation_after_simplify
            })

        return {
            "success": True,
            "iterations": iteration_count,
            "balanced_equation": str(known),
            "balancing_history": history
        }
    else:
        _simplify_coefficients(known)

        return {
            "success": False,
            "error_message": f"KHÔNG tìm được lời giải sau {max_iterations} lần lặp. Thử tăng MAX_ITERATIONS.",
            "unbalanced_result": str(known),
            "iterations": iteration_count,
            "balancing_history": history,
            "unbalanced_details": _get_unbalanced_details(known)
        }