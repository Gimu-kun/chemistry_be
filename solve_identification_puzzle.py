import collections
from typing import List, Dict, Tuple, Any


def solve_identification_puzzle(
        unknown_list: List[str],
        test_matrix: Dict[Tuple[str, str], str]
) -> Dict[str, Any]:
    """
    Giải bài toán nhận biết hóa chất bị mất nhãn dựa trên ma trận hiện tượng.

    Args:
        unknown_list: Danh sách các hóa chất cần nhận biết (ví dụ: ["A", "B", "C"]).
        test_matrix: Ma trận kết quả thử nghiệm (cặp chất: hiện tượng).
                     Ví dụ: {('A', 'B'): 'Ket tua trang', ('A', 'C'): 'Khong phan ung'}

    Returns:
        Một dictionary chứa các bước nhận biết và kết quả cuối cùng.
    """

    # 1. Khởi tạo
    # Nhóm ban đầu: Tất cả các chất chưa được nhận biết.
    current_group: List[str] = list(unknown_list)

    # Kết quả sẽ lưu trữ các bước nhận biết (Step-by-step)
    steps_history: List[Dict[str, Any]] = []

    # Map để lưu kết quả nhận dạng cuối cùng: {Tên chất: 'Lọ X'}
    final_mapping: Dict[str, str] = {}

    # Lọ nhãn tạm thời (dùng A, B, C... làm nhãn giả định)
    temp_labels: List[str] = [f"Lo_{i + 1}" for i in range(len(unknown_list))]

    # Map nhãn giả định với chất hóa học
    # Ví dụ: assumed_labels_map['Na2SO4'] = 'Lo_1'
    assumed_labels_map: Dict[str, str] = dict(zip(current_group, temp_labels))

    step_count = 0

    # 2. Lặp lại cho đến khi tất cả các chất đều được nhận biết
    while len(current_group) > 0 and step_count < 10:  # Giới hạn số bước lặp để tránh vòng lặp vô tận
        step_count += 1

        # 2.1. Chọn chất thử (Reference Chemical)
        # Chất đầu tiên trong nhóm chưa được nhận biết được chọn làm chất tham chiếu để thử nghiệm
        reference_chemical = current_group[0]

        # 2.2. Xây dựng bản đồ hiện tượng: {Hiện tượng: [Các chất có hiện tượng đó]}
        # Ví dụ: {'Ket tua trang': ['Na2SO4', 'NaCl'], 'Khong phan ung': ['NaNO3']}
        phenomena_groups: Dict[str, List[str]] = collections.defaultdict(list)

        # Lưu trữ kết quả thử nghiệm chi tiết cho bước này
        current_test_results: List[Dict[str, str]] = []

        # Lấy nhãn giả định của chất tham chiếu (ví dụ: 'Lo_1')
        ref_label = assumed_labels_map[reference_chemical]

        # Thử nghiệm chất tham chiếu (reference_chemical) với TẤT CẢ các chất còn lại
        for target_chemical in current_group:
            if reference_chemical == target_chemical:
                # Chất tự phản ứng với chính nó không cung cấp thông tin phân biệt, bỏ qua.
                continue

            # Chuẩn hóa cặp chất theo thứ tự chữ cái để tra cứu ma trận
            pair = tuple(sorted((reference_chemical, target_chemical)))
            phenomenon = test_matrix.get(pair, 'Khong phan ung')

            # Thêm vào nhóm hiện tượng
            phenomena_groups[phenomenon].append(target_chemical)

            # Lưu lại kết quả thử nghiệm cho báo cáo
            current_test_results.append({
                "chemical_pair": f"{ref_label} ({reference_chemical}) + {assumed_labels_map[target_chemical]} ({target_chemical})",
                "phenomenon": phenomenon
            })

        # 2.3. Phân tích kết quả và Nhận dạng
        newly_identified: List[str] = []
        next_group_to_process: List[str] = []

        action = f"Sử dụng chất {ref_label} ({reference_chemical}) làm thuốc thử để phân loại nhóm còn lại."

        # Duyệt qua các nhóm hiện tượng (vd: 'Ket tua trang', 'Khi thoat ra', 'Khong phan ung')
        for phenomenon, chemicals_in_group in phenomena_groups.items():

            # Nếu chỉ có 1 chất cho ra hiện tượng ĐỘC NHẤT VÀ KHÁC LẠ (phenomenon)
            # so với chất tham chiếu (reference_chemical), thì chất đó được nhận dạng.
            # Ví dụ: BaCl2 + Na2SO4 = Kết tủa trắng. BaCl2 + HCl = Không PƯ.
            # Nếu "Ket tua trang" chỉ xuất hiện 1 lần, thì ta đã nhận dạng được Na2SO4.
            if len(chemicals_in_group) == 1:
                identified_chemical = chemicals_in_group[0]

                # Chất có hiện tượng độc nhất phải được đối chiếu lại với chất tham chiếu (reference_chemical)
                # để xác nhận 100% không phải là chất tham chiếu.
                if identified_chemical != reference_chemical:
                    newly_identified.append(identified_chemical)
                    action += f" | Chất {assumed_labels_map[identified_chemical]} được nhận dạng là {identified_chemical} vì hiện tượng '{phenomenon}' là DUY NHẤT so với {ref_label}."

            elif len(chemicals_in_group) > 1:
                # Nếu nhóm có 2 chất trở lên có cùng hiện tượng, cần tiếp tục phân loại ở vòng lặp sau
                next_group_to_process.extend(chemicals_in_group)

        # 2.4. Cập nhật nhóm và lịch sử
        # Chất tham chiếu (reference_chemical) luôn được coi là đã được phân loại ở bước này.
        current_group_before = list(current_group)
        current_group.clear()

        # Thêm chất tham chiếu và các chất được nhận dạng
        all_identified_in_step = [reference_chemical] + newly_identified

        for chem in all_identified_in_step:
            if chem in current_group_before:
                final_mapping[chem] = assumed_labels_map[chem]

        # Cập nhật nhóm cho vòng lặp tiếp theo
        # Loại bỏ các chất đã được nhận dạng khỏi nhóm cần xử lý tiếp theo
        for chem in next_group_to_process:
            if chem not in final_mapping and chem not in current_group:
                current_group.append(chem)

        # Lưu lịch sử bước
        steps_history.append({
            "step": step_count,
            "action": action,
            "reference_chemical": f"{ref_label} ({reference_chemical})",
            "test_results": current_test_results,
            "identified_in_step": [f"{assumed_labels_map[c]} ({c})" for c in newly_identified if
                                   c in current_group_before],
            "remaining_chemicals": [f"{assumed_labels_map[c]} ({c})" for c in current_group]
        })

        # Nếu không có chất nào được nhận dạng trong bước này, ta cần thay đổi chất tham chiếu
        if not newly_identified and len(current_group) < len(current_group_before):
            # Cần một logic phức tạp hơn (vd: chia nhóm không dựa vào độc nhất mà dựa vào sự khác biệt)
            # Đối với triển khai này, ta chỉ cần đảm bảo chất tham chiếu tiếp theo là một chất khác
            # trong nhóm còn lại (logic này đã được xử lý bằng cách lấy current_group[0] tiếp theo)
            pass

    # 3. Kết quả cuối cùng
    result_summary = {
        "identified_mapping": {label: chem for chem, label in final_mapping.items()},
        "unidentified_chemicals": current_group,
        "identification_steps": steps_history,
        "success": len(final_mapping) == len(unknown_list)
    }

    return result_summary