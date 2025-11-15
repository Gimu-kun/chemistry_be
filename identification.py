from typing import List, Dict, Tuple, Any

from forward_chaining import run_forward_chaining
from models import ReactionModel
from solve_identification_puzzle import solve_identification_puzzle


def identify_chemicals(unknown_list: List[str]) -> Dict:
    """Xây dựng ma trận thử nghiệm và gọi hàm giải."""

    # Chuẩn hóa danh sách đầu vào để đảm bảo tính nhất quán (vd: loại bỏ khoảng trắng, sắp xếp)
    clean_list = [c.strip() for c in unknown_list]

    test_matrix: Dict[Tuple[str, str], str] = {}

    # 1. Xây dựng ma trận thử nghiệm
    for i, chemical_A in enumerate(clean_list):
        for j, chemical_B in enumerate(clean_list):
            if i >= j: continue

            # 1.1. Chuẩn bị đầu vào cho forward_chaining
            reactants_str = f"{chemical_A} + {chemical_B}"

            # Trong các bài nhận biết dung dịch, điều kiện thường là rỗng (phòng thí nghiệm)
            conditions_str = ""

            # 1.2. Chạy suy luận tiến
            result = run_forward_chaining(reactants_str, conditions_str)

            # 1.3. Trích xuất hiện tượng
            phenomenon = "Khong phan ung"
            if result and result.get('reactions_used'):
                # Lấy hiện tượng từ phản ứng đầu tiên
                first_reaction = result['reactions_used'][0]

                # CẦN ĐẢM BẢO run_forward_chaining trả về trường 'phenomena'
                # Nếu ReactionModel đã được cập nhật, bạn cần chỉnh sửa forward_chaining.py
                # để thêm 'phenomena' vào dictionary 'used_rules_info'.
                phenomenon = first_reaction.get('phenomena', 'Phan ung xay ra (khong ro hien tuong)')

                # Chuẩn hóa cặp chất theo thứ tự chữ cái để sử dụng làm key
            key = tuple(sorted((chemical_A, chemical_B)))
            test_matrix[key] = phenomenon

    # 2. Gọi hàm giải câu đố
    identification_result = solve_identification_puzzle(clean_list, test_matrix)

    return identification_result