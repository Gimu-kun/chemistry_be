import collections
import re
import json  # Vẫn giữ lại nếu cần dùng sau này
from typing import List, Dict, Any, TYPE_CHECKING

# Giả định cho Type Hinting nếu cần (Tránh lỗi import vòng tròn nếu models.py import chemistry_data)
if TYPE_CHECKING:
    from models import ReactionModel

# Các hằng số (Constants)
MAX_ELEMENTS_PER_COMPOUND = 5
MAX_COMPOUNDS_PER_SIDE = 5
MAX_UNIQUE_ELEMENTS = 10
MAX_COEFFICIENTS = MAX_COMPOUNDS_PER_SIDE * 2

# Dữ liệu nguyên tố (Periodic Table Data)
ELEMENTS: Dict[str, Dict[str, Any]] = {
    "H": {"num": 1, "mass": 1.008, "valence": 1},
    "He": {"num": 2, "mass": 4.0026, "valence": 0},
    # ... (Giữ nguyên toàn bộ dữ liệu ELEMENTS của bạn) ...
    "Og": {"num": 118, "mass": 294.0, "valence": 0}
}


# ======================================================================
# LỚP COMPOUND VÀ EQUATION (GIỮ NGUYÊN)
# ======================================================================

class Compound:
    """Đại diện cho một chất hóa học (hợp chất hoặc nguyên tố)."""

    # ... (Giữ nguyên class Compound) ...
    def __init__(self, name, coefficient=1):
        self.name = name
        self.coefficient = coefficient
        self.elements = self._parse_formula(name)

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


class ChemicalEquation:
    """Đại diện cho một phương trình hóa học."""

    # ... (Giữ nguyên class ChemicalEquation) ...
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
# QUẢN LÝ DỮ LIỆU CACHE TOÀN CỤC (SỬ DỤNG ReactionModel)
# ======================================================================

# Biến này giờ chứa List[ReactionModel]
REACTION_RULES_CACHED: List[Any] = []
REACTION_RULES: List[Any] = REACTION_RULES_CACHED


def initialize_reactions_database() -> List[Any]:
    # ... (Giữ nguyên) ...
    if not REACTION_RULES_CACHED:
        print("Cảnh báo: REACTION_RULES_CACHED rỗng. Hãy đảm bảo load_reactions_from_db được gọi.")
    return REACTION_RULES_CACHED


def load_reactions_from_db(models_module) -> List[Any]:
    """
    Tải dữ liệu ReactionModel từ CSDL vào bộ nhớ và cập nhật biến toàn cục.
    """
    global REACTION_RULES_CACHED, REACTION_RULES
    ReactionModel = models_module.ReactionModel

    print("\n[DEBUG] BẮT ĐẦU TẢI DỮ LIỆU TỪ CSDL...")

    try:
        # Lấy trực tiếp các đối tượng ReactionModel đã được nạp
        all_models = ReactionModel.query.all()

        num_models = len(all_models)
        print(f"[DEBUG] Số lượng bản ghi truy vấn được từ CSDL: {num_models}")

        if num_models == 0:
            print("[DEBUG] CẢNH BÁO: ReactionModel.query.all() trả về danh sách trống. CSDL có thể chưa có dữ liệu.")
            REACTION_RULES_CACHED = []
            REACTION_RULES = []
            return []

        # >>> BƯỚC KIỂM TRA: Vẫn kiểm tra decode JSON
        first_model = all_models[0]
        # Sử dụng .to_dict() để đảm bảo quá trình decode JSON hoạt động đúng
        first_data = first_model.to_dict()
        print(f"[DEBUG] Dữ liệu chuyển đổi của bản ghi đầu tiên: {first_data}")

        # Gán trực tiếp list các đối tượng ReactionModel vào cache
        cached_rules = all_models

        # CẬP NHẬT CẢ HAI BIẾN TOÀN CỤC
        REACTION_RULES_CACHED = cached_rules
        REACTION_RULES = cached_rules

        print(
            f"\n[DEBUG] ĐÃ HOÀN TẤT TẢI: Đã tải thành công {len(REACTION_RULES_CACHED)} luật phản ứng từ CSDL vào bộ nhớ.")
        return REACTION_RULES_CACHED

    except Exception as e:
        print(f"\n[DEBUG] LỖI CẤP CAO: LỖI TẢI DỮ LIỆU TỪ CSDL: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_reaction_rules() -> List[Any]:
    """Trả về danh sách các luật phản ứng đã được cache (ReactionModel objects)."""
    return REACTION_RULES


# CẬP NHẬT: Hàm này giờ nhận vào một ReactionModel object
def is_react_available(reaction: Any, known_facts: set, initial_conditions: set, check_conditions: bool = True) -> bool:
    """Kiểm tra xem một phản ứng có thể xảy ra hay không."""
    # ReactionModel đã có thuộc tính .is_used
    if reaction.is_used:
        return False

    # 1. Kiểm tra chất phản ứng có sẵn không (Sử dụng property mới từ ReactionModel)
    if not all(r in known_facts for r in reaction.required_reactants):
        return False

    # 2. Kiểm tra điều kiện có sẵn không (Sử dụng property mới từ ReactionModel)
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