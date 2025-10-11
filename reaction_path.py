from chemistry_data import parse_input_to_set, is_react_available, get_reaction_rules
# Import ReactionModel từ models để sử dụng cho Type Hinting và object
import models
from typing import List, Dict, Union, Any, Set

# Gán ReactionModel cho một alias dễ đọc hơn trong file này
Reaction = models.ReactionModel


def _reaction_to_dict(reaction: Reaction) -> Dict[str, Any]:
    """
    Chuyển đổi ReactionModel object thành dictionary để trả về API.
    Sử dụng các property và trường đã có của ReactionModel.
    """
    # Dùng to_dict() của ReactionModel để lấy các thuộc tính đã decode JSON
    data = reaction.to_dict()

    # Bổ sung các thông tin khác cần thiết cho API
    data["is_used"] = reaction.is_used

    # Lấy chuỗi phương trình từ __repr__ hoặc từ trường equation_string nếu có
    # Ta sẽ dùng str(reaction) để lấy chuỗi repr đã được định dạng
    repr_lines = str(reaction).split('\n')
    equation_line = next((line for line in repr_lines if line.startswith("Phương trình:")), None)

    # Lấy chuỗi phương trình từ line thứ 3 của repr
    data["equation_string"] = equation_line.replace("Phương trình: ", "").strip() if equation_line else data.get(
        "equation_string", "N/A")

    # Đảm bảo các key cũ vẫn tồn tại cho tính tương thích API
    data["reactants"] = data.pop("reactants", [])
    data["conditions"] = data.pop("conditions", [])

    return data


def _reconstruct_path(target: str, path_map: Dict[str, Reaction]) -> List[Reaction]:
    """Tái tạo chuỗi phản ứng từ đích đến chất ban đầu."""
    reaction_chain: List[Reaction] = []
    current_chemical = target
    temp_path_map = path_map.copy()

    while current_chemical in temp_path_map:
        reaction = temp_path_map[current_chemical]
        reaction_chain.append(reaction)
        del temp_path_map[current_chemical]

        next_chemical = None
        # Tìm chất phản ứng cần thiết để tạo ra sản phẩm này
        for reactant in reaction.required_reactants:
            # Nếu chất phản ứng này được tạo ra từ một phản ứng khác (nó có trong path_map)
            if reactant in path_map:
                next_chemical = reactant
                break

        if next_chemical:
            current_chemical = next_chemical
        else:
            break

    reaction_chain.reverse()
    return reaction_chain


def find_reaction_path(initial_reactants_str: str, target_chemical: str) -> Dict[str, Any]:
    # KHÔNG CẦN TẠO BẢN SAO VÀ CHUYỂN ĐỔI SANG Reaction nữa.
    # Ta sử dụng trực tiếp các đối tượng ReactionModel trong REACTION_RULES.
    rules: List[Reaction] = get_reaction_rules()

    # Đặt lại cờ is_used cho tất cả các luật trước khi chạy thuật toán
    for r in rules:
        r.is_used = False

    known_facts: Set[str] = parse_input_to_set(initial_reactants_str, '+')
    target_chemical = target_chemical.strip()

    # path_map lưu trữ {sản phẩm: phản ứng tạo ra nó}
    path_map: Dict[str, Reaction] = {}

    something_new_deduced = True
    iteration_count = 0
    target_found = False

    while something_new_deduced and not target_found:
        something_new_deduced = False
        iteration_count += 1

        for r in rules:
            # Kiểm tra xem phản ứng có thể xảy ra với các chất hiện có không
            if is_react_available(r, known_facts, set(), check_conditions=False):
                r.is_used = True

                for new_product in r.products:  # Sử dụng property .products từ ReactionModel
                    if new_product not in known_facts:
                        known_facts.add(new_product)
                        path_map[new_product] = r
                        something_new_deduced = True

                        if new_product == target_chemical:
                            target_found = True
                            break
                if target_found: break
            if target_found: break

    if target_found:
        reaction_path_objects = _reconstruct_path(target_chemical, path_map)

        # Chuyển đổi chuỗi phản ứng (ReactionModel objects) sang dict
        path_serializable = [_reaction_to_dict(r) for r in reaction_path_objects]

        known_chemicals_list = sorted(list(known_facts))

        return {
            "success": True,
            "target": target_chemical,
            "path_steps": iteration_count,
            "path": path_serializable,
            "known_chemicals": known_chemicals_list
        }
    else:
        return {
            "success": False,
            "error_message": f"Không tìm thấy đường phản ứng để tạo ra '{target_chemical}'."
        }