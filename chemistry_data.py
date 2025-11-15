# --- File: chemistry_data.py ---

import collections
import math
import re
import json
import traceback
from typing import List, Dict, Any, TYPE_CHECKING, Optional, Set
from collections import deque

# Giả định cho Type Hinting nếu cần (Tránh lỗi import vòng tròn nếu models.py import chemistry_data)
if TYPE_CHECKING:
    from models import ReactionModel, ChemicalRuleModel, ElementModel

# ======================================================================
# HẰNG SỐ VÀ CACHE DỮ LIỆU TOÀN CỤC
# ======================================================================

MAX_ELEMENTS_PER_COMPOUND = 5
MAX_COMPOUNDS_PER_SIDE = 5
MAX_UNIQUE_ELEMENTS = 10
MAX_COEFFICIENTS = MAX_COMPOUNDS_PER_SIDE * 2

# Cache dữ liệu nguyên tố (sẽ được tải từ CSDL)
ELEMENTS_CACHED: Dict[str, Dict[str, Any]] = {}
ELEMENTS: Dict[str, Dict[str, Any]] = ELEMENTS_CACHED  # Trỏ ELEMENTS đến cache

# Biến toàn cục cho Luật Phản ứng (Reaction Rules)
REACTION_RULES_CACHED: List[Any] = []
REACTION_RULES: List[Any] = REACTION_RULES_CACHED

# Biến toàn cục cho Luật Hóa học Chung (Chemical Rules)
CHEMICAL_RULES_CACHED: List[Any] = []
CHEMICAL_RULES: List[Any] = CHEMICAL_RULES_CACHED


# ======================================================================
# LỚP COMPOUND (Đại diện cho chất hóa học)
# ======================================================================

class Compound:
    """Đại diện cho một chất hóa học (hợp chất hoặc nguyên tố)."""

    def __init__(self, name, coefficient=1):
        self.name = name
        self.coefficient = coefficient
        self.elements = self._parse_formula(name)

    # (Giữ nguyên các hàm _parse_formula, _remove_state_and_ion_groups,
    # _replicate_group_elements)

    def _parse_formula(self, formula):
        counts = collections.defaultdict(int)
        temp_formula = self._remove_state_and_ion_groups(formula)

        i = 0
        while i < len(temp_formula):
            if temp_formula[i].isupper():
                element = temp_formula[i]
                i += 1
                if i < len(temp_formula) and temp_formula[i].islower():
                    element += temp_formula[i]
                    i += 1

                subscript = ""
                while i < len(temp_formula) and temp_formula[i].isdigit():
                    subscript += temp_formula[i]
                    i += 1

                count = int(subscript) if subscript else 1
                counts[element] += count
            else:
                i += 1
        return dict(counts)

    def _remove_state_and_ion_groups(self, formula):
        temp_formula = formula.strip()
        temp_formula = re.sub(r'\(([sldgq]|aq)\)', '', temp_formula)
        while '(' in temp_formula and ')' in temp_formula:
            start = temp_formula.rfind('(')
            end = temp_formula.find(')', start)
            if start == -1 or end == -1: break
            group = temp_formula[start + 1:end]
            subscript = ""
            i = end + 1
            while i < len(temp_formula) and temp_formula[i].isdigit():
                subscript += temp_formula[i]
                i += 1
            count = int(subscript) if subscript else 1
            processed_group = self._replicate_group_elements(group, count)
            temp_formula = temp_formula[:start] + processed_group + temp_formula[i:]
        temp_formula = temp_formula.replace('(', '').replace(')', '')
        return temp_formula.strip()

    def _replicate_group_elements(self, group, count):
        processed = ""
        j = 0
        while j < len(group):
            element = group[j]
            j += 1
            if j < len(group) and group[j].islower():
                element += group[j]
                j += 1
            subscript = ""
            while j < len(group) and group[j].isdigit():
                subscript += group[j]
                j += 1
            original_count = int(subscript) if subscript else 1
            new_count = original_count * count
            processed += element
            if new_count > 1: processed += str(new_count)
        return processed

    def __str__(self):
        return f"{self.coefficient}{self.name}" if self.coefficient > 1 else self.name


# ======================================================================
# LỚP CHEMICAL EQUATION (Giữ nguyên)
# ======================================================================

class ChemicalEquation:
    """Đại diện cho một phương trình hóa học."""

    def __init__(self, reactants, products):
        self.reactants = [Compound(r) for r in reactants]
        self.products = [Compound(p) for p in products]

    def get_element_totals(self):
        left_totals = collections.defaultdict(int)
        right_totals = collections.defaultdict(int)
        all_elements = set()

        for comp in self.reactants:
            for element, count in comp.elements.items():
                left_totals[element] += count * comp.coefficient
                all_elements.add(element)

        for comp in self.products:
            for element, count in comp.elements.items():
                right_totals[element] += count * comp.coefficient
                all_elements.add(element)

        return left_totals, right_totals, all_elements

    def is_balanced(self):
        left, right, _ = self.get_element_totals()
        return all(left[e] == right[e] for e in left) and all(right[e] == left[e] for e in right)

    def __str__(self):
        left_str = " + ".join(str(c) for c in self.reactants)
        right_str = " + ".join(str(c) for c in self.products)
        return f"{left_str} -> {right_str}"


# ======================================================================
# CHỨC NĂNG TẢI DỮ LIỆU TỪ CSDL VÀ QUẢN LÝ CACHE
# ======================================================================

def load_elements_from_db(models_module) -> Dict[str, Dict[str, Any]]:
    """
    Tải dữ liệu Bảng Tuần Hoàn từ CSDL (bảng 'elements') vào bộ nhớ.
    """
    global ELEMENTS_CACHED, ELEMENTS

    ElementModel = getattr(models_module, 'ElementModel', None)

    if not ElementModel:
        print("[LỖI TẢI ELEMENT] Không tìm thấy ElementModel. Đảm bảo đã định nghĩa.")
        return ELEMENTS_CACHED

    print("\n[SETUP] BẮT ĐẦU TẢI DỮ LIỆU BẢNG TUẦN HOÀN...")
    new_elements_cache = {}

    try:
        all_elements = ElementModel.query.all()

        print(all_elements)
        for element in all_elements:
            new_elements_cache[element.mark] = {
                'num': element.atomic_number,
                'mass': element.atomic_mass,
                'valence': element.valence
            }

        ELEMENTS_CACHED = new_elements_cache
        ELEMENTS = ELEMENTS_CACHED
        print(f"[SETUP] ĐÃ HOÀN TẤT TẢI: {len(ELEMENTS_CACHED)} nguyên tố đã được tải.")

    except Exception as e:
        print(f"[LỖI SETUP] LỖI TẢI DỮ LIỆU BẢNG TUẦN HOÀN: {e}")
        traceback.print_exc()

    return ELEMENTS_CACHED


def load_reactions_from_db(models_module) -> List[Any]:
    global REACTION_RULES_CACHED, REACTION_RULES
    ReactionModel = models_module.ReactionModel
    try:
        all_models = ReactionModel.query.all()
        REACTION_RULES_CACHED = all_models
        REACTION_RULES = all_models
        print(f"\n[DEBUG] ĐÃ HOÀN TẤT TẢI: {len(REACTION_RULES)} luật phản ứng.")
        return REACTION_RULES
    except Exception as e:
        print(f"\n[DEBUG] LỖI TẢI LUẬT PHẢN ỨNG: {e}")
        return []


def load_chemical_rules_from_db(models_module) -> List[Any]:
    """
    Tải dữ liệu ChemicalRuleModel từ CSDL vào bộ nhớ và cập nhật biến toàn cục CHEMICAL_RULES.
    """
    global CHEMICAL_RULES_CACHED, CHEMICAL_RULES
    ChemicalRuleModel = getattr(models_module, 'ChemicalRuleModel', None)

    if not ChemicalRuleModel:
        # Fallback hoặc cảnh báo nếu lớp model không được tìm thấy
        print("[WARNING] Không tìm thấy ChemicalRuleModel.")
        return []

    print("\n[SETUP] BẮT ĐẦU TẢI DỮ LIỆU LUẬT HÓA HỌC CHUNG...")

    try:
        all_models = ChemicalRuleModel.query.all()

        num_models = len(all_models)
        CHEMICAL_RULES_CACHED = all_models
        CHEMICAL_RULES = all_models

        print(f"[SETUP] ĐÃ HOÀN TẤT TẢI: Đã tải thành công {num_models} luật hóa học chung.")

        return CHEMICAL_RULES_CACHED

    except Exception as e:
        print(f"[LỖI SETUP] LỖI TẢI LUẬT HÓA HỌC CHUNG TỪ CSDL: {e}")
        traceback.print_exc()
        return []


def get_reaction_rules() -> List[Any]:
    """Trả về danh sách các luật phản ứng đã được cache (ReactionModel objects)."""
    return REACTION_RULES


def get_chemical_rules() -> List[Any]:
    """Trả về danh sách các luật hóa học chung đã được cache."""
    return CHEMICAL_RULES


# ======================================================================
# CHỨC NĂNG TÍNH TOÁN VÀ SUY LUẬN
# ======================================================================

def get_molar_mass(formula: str) -> float:
    """
    Tính khối lượng mol (M) của một công thức hóa học, sử dụng dữ liệu ELEMENTS_CACHED.
    """
    try:
        compound = Compound(formula)
        molar_mass = 0.0
        for element_symbol, count in compound.elements.items():
            if element_symbol in ELEMENTS:
                atomic_mass = ELEMENTS[element_symbol]['mass']
                molar_mass += atomic_mass * count
            else:
                raise ValueError(f"Nguyên tố '{element_symbol}' không được tìm thấy trong bảng tuần hoàn.")

        return round(molar_mass, 3)

    except ValueError as e:
        raise ValueError(f"Lỗi tính Khối lượng Mol cho {formula}: {e}")
    except Exception:
        raise ValueError(f"Không thể phân tích hoặc tính Khối lượng Mol cho công thức: {formula}")


def execute_rule_expression(expression: str, inputs: Dict[str, float]) -> float:
    """
    Thực thi biểu thức tính toán an toàn (ví dụ: 'm / M_A').
    """
    allowed_globals = {
        'math': math,
        '__builtins__': None
    }

    local_vars = inputs.copy()

    try:
        local_vars['abs'] = abs
        local_vars['log10'] = math.log10

        result = eval(expression, allowed_globals, local_vars)
        return float(result)
    except NameError as e:
        raise ValueError(f"Lỗi cú pháp trong biểu thức (thiếu biến): {e}")
    except ZeroDivisionError:
        raise ValueError("Lỗi chia cho 0 trong phép tính.")
    except Exception as e:
        raise ValueError(f"Lỗi thực thi biểu thức: {e}")


def find_calculation_path(known_vars: Set[str], target_var: str, all_rules: List[Any]) -> Optional[
    List[Dict[str, Any]]]:
    """
    Tìm chuỗi luật tính toán...
    """
    queue = deque([(known_vars, [])])
    visited_states = {tuple(sorted(known_vars))}
    max_steps = 10

    while queue and len(queue[0][1]) < max_steps:
        current_vars, current_path = queue.popleft()

        if target_var in current_vars:
            # Mục tiêu đã đạt được. Trả về đường đi.
            # Dùng .to_dict() cho Model, giữ nguyên dict cho Custom Rule
            return [step.to_dict() if hasattr(step, 'to_dict') else step for step in current_path]

        for rule in all_rules:
            # === PHẦN SỬA LỖI TẠI ĐÂY ===
            # Chuyển rule sang dict để xử lý thống nhất
            rule_data = rule.to_dict() if hasattr(rule, 'to_dict') else rule

            output_var = rule_data['output_var']
            required_inputs = rule_data['required_inputs']  # Đã là list/dict nhờ JSONEncodedDict hoặc dict
            # ============================

            can_be_applied = all(var in current_vars for var in required_inputs)
            is_new_and_useful = output_var not in current_vars

            if can_be_applied and is_new_and_useful:
                new_vars = current_vars.union({output_var})
                new_state = tuple(sorted(new_vars))

                if new_state not in visited_states:
                    new_path = current_path + [rule]  # Lưu trữ đối tượng Model/Dict gốc
                    visited_states.add(new_state)
                    queue.append((new_vars, new_path))

    return None


# ======================================================================
# CÁC HÀM HỖ TRỢ PHẢN ỨNG (Giữ nguyên)
# ======================================================================

def is_react_available(reaction: Any, known_facts: set, initial_conditions: set, check_conditions: bool = True) -> bool:
    """Kiểm tra xem một phản ứng có thể xảy ra hay không (dành cho ReactionModel)."""
    print("known_facts",known_facts)
    if reaction.is_used:
        return False

    if not all(r in known_facts for r in reaction.required_reactants):
        return False

    if check_conditions and reaction.required_conditions:
        if not all(c in initial_conditions for c in reaction.required_conditions):
            return False

    return True


def parse_input_to_set(input_str: str, delimiter='+') -> set:
    """Chuyển đổi chuỗi đầu vào (phản ứng/điều kiện) thành một set."""
    if not input_str:
        return set()
    items = [item.strip() for item in input_str.split(delimiter)]
    return set(item for item in items if item)