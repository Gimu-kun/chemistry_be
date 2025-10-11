from chemistry_data import REACTION_RULES, parse_input_to_set, is_react_available, get_reaction_rules
import copy


# Giả định get_reaction_rules() trả về các đối tượng cần được reset trạng thái.
def run_forward_chaining(initial_reactants_str: str, reaction_conditions_str: str) -> dict:
    """
    Thực hiện suy luận tiến để tìm các sản phẩm của phản ứng hóa học
    dựa trên tập hợp các quy tắc đã định sẵn (Chuỗi phản ứng).

    Nếu reaction_conditions_str rỗng, coi như mọi điều kiện đều được chấp nhận.
    """
    # Khởi tạo
    rules = copy.deepcopy(get_reaction_rules())
    for r in rules: r.is_used = False

    known_facts = parse_input_to_set(initial_reactants_str, '+')

    # Xử lý điều kiện đầu vào
    input_conditions_set = parse_input_to_set(reaction_conditions_str, ',')

    # Cờ để quyết định có nên kiểm tra điều kiện bắt buộc của quy tắc hay không.
    # Nếu người dùng KHÔNG nhập điều kiện (set rỗng), ta KHÔNG kiểm tra điều kiện bắt buộc của quy tắc.
    check_conditions_flag = len(input_conditions_set) > 0

    all_deduced_products = set()
    used_rules_info = []
    first_reaction_summary = None

    something_new_deduced = True
    iteration_count = 0

    while something_new_deduced:
        something_new_deduced = False
        iteration_count += 1
        newly_deduced_products = set()

        for r in rules:
            # Chỉ kiểm tra các quy tắc chưa được sử dụng thành công
            # TRUYỀN input_conditions_set và check_conditions_flag VÀO is_react_available
            if not r.is_used and is_react_available(r, known_facts, input_conditions_set,
                                                    check_conditions=check_conditions_flag):

                # 1. Ghi nhận quy tắc đã được sử dụng
                r.is_used = True

                # 2. Tạo chuỗi phản ứng cho báo cáo chi tiết
                reaction_summary = f"{' + '.join(r.required_reactants)}{f' [{', '.join(r.required_conditions)}]' if r.required_conditions else ''} -> {' + '.join(r.products)}"

                # Lưu phản ứng đầu tiên/tiêu biểu
                if first_reaction_summary is None:
                    first_reaction_summary = reaction_summary

                # Lưu thông tin chi tiết phản ứng vào danh sách kết quả (từng bước)
                used_rules_info.append({
                    "type": r.type,
                    "description": r.description,
                    "reaction": reaction_summary
                })

                # 3. Thêm sản phẩm mới vào Known Facts
                for new_product in r.products:
                    if new_product not in known_facts:
                        known_facts.add(new_product)
                        newly_deduced_products.add(new_product)
                        something_new_deduced = True

        all_deduced_products.update(newly_deduced_products)

    # Trả về kết quả tổng hợp
    return {
        "reactions": first_reaction_summary if first_reaction_summary else "Không có phản ứng nào được kích hoạt",
        "type": "Phân tích chuỗi phản ứng",
        "description": "Kết quả suy luận tiến dựa trên các chất ban đầu và điều kiện.",
        "final_products": sorted(list(all_deduced_products)),
        "total_facts": sorted(list(known_facts)),
        "initial_reactants": sorted(list(parse_input_to_set(initial_reactants_str, '+'))),
        "iterations": iteration_count,
        "reactions_used": used_rules_info,
        "summary": f"Đã sử dụng {len(used_rules_info)} quy tắc để suy luận ra {len(all_deduced_products)} sản phẩm mới."
    }