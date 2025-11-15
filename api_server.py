from typing import Dict, List
import json
import traceback
from urllib.parse import quote_plus

from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import deque

# Import modules
import models
from balancer import balance_equation
from forward_chaining import run_forward_chaining
from identification import identify_chemicals
from models import db, ReactionModel, ChemicalRuleModel

# Import các hàm từ logic hóa học
from chemistry_data import (
    load_reactions_from_db, get_reaction_rules,
    load_chemical_rules_from_db, get_chemical_rules,
    execute_rule_expression, find_calculation_path,
    get_molar_mass, load_elements_from_db,
    Compound
)
from reaction_path import find_reaction_path

# Khởi tạo Flask App
app = Flask(__name__)
CORS(app)

# ======================================================================
# CẤU HÌNH CSDL (Giữ nguyên)
# ======================================================================

DB_USER = 'root'
DB_PASSWORD_ENCODED = quote_plus('June1996@')
DB_HOST = '127.0.0.1'
DB_NAME = 'chemistry'

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD_ENCODED}@{DB_HOST}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


# ======================================================================
# HÀM SETUP CSDL VÀ TẢI DỮ LIỆU VÀO BỘ NHỚ (Giữ nguyên)
# ======================================================================

def setup_database(app):
    """
    Thiết lập CSDL (tạo bảng nếu chưa có) và tải tất cả luật, bao gồm Bảng Tuần Hoàn, vào bộ nhớ.
    """
    with app.app_context():
        try:
            db.create_all()
            print("Đã kiểm tra và đảm bảo các bảng CSDL đã tồn tại.")

            # 1. TẢI DỮ LIỆU BẢNG TUẦN HOÀN (ELEMENTS)
            print("\n[SETUP] BẮT ĐẦU TẢI DỮ LIỆU BẢNG TUẦN HOÀN VÀO BỘ NHỚ...")
            loaded_elements = load_elements_from_db(models)
            print(f"\n--- CHI TIẾT DỮ LIỆU NGUYÊN TỐ ĐÃ TẢI ---")
            if loaded_elements:
                print(f"TỔNG CỘNG: ĐÃ TẢI THÀNH CÔNG {len(loaded_elements)} nguyên tố.")
                first_three = {k: v for i, (k, v) in enumerate(loaded_elements.items()) if i < 3}
                print(f"[KIỂM TRA] 3 Nguyên tố đầu tiên: {first_three}")
            else:
                print("CẢNH BÁO: Không tìm thấy dữ liệu nguyên tố nào.")
            print("------------------------------------------\n")

            # 2. TẢI LUẬT PHẢN ỨNG (REACTION RULES)
            print("\n[SETUP] BẮT ĐẦU TẢI DỮ LIỆU PHẢN ỨNG VÀO BỘ NHỚ...")
            load_reactions_from_db(models)
            current_reaction_rules = get_reaction_rules()
            print(f"\n--- DANH SÁCH PHẢN ỨNG ĐÃ TẢI ({len(current_reaction_rules)}) ---")
            if current_reaction_rules:
                print(f"[KIỂM TRA] Bản ghi đầu tiên: {current_reaction_rules[0].to_dict()}")
            else:
                print("CẢNH BÁO: Không tìm thấy luật phản ứng nào.")
            print("------------------------------------------\n")

            # 3. TẢI LUẬT HÓA HỌC CHUNG (CHEMICAL RULES)
            print("[SETUP] BẮT ĐẦU TẢI DỮ LIỆU LUẬT HÓA HỌC CHUNG VÀO BỘ NHỚ...")
            load_chemical_rules_from_db(models)
            current_chemical_rules = get_chemical_rules()
            print(f"\n--- CHI TIẾT LUẬT HÓA HỌC CHUNG ĐÃ TẢI ({len(current_chemical_rules)}) ---")
            if current_chemical_rules:
                for i, rule_model in enumerate(current_chemical_rules[:5]):
                    rule_data = rule_model.to_dict()
                    print(f"\n[{i + 1}] Tên: {rule_data.get('name')}, Đầu ra: {rule_data.get('output_var')}")
                    if len(current_chemical_rules) > 5 and i == 4:
                        print(f"... và {len(current_chemical_rules) - 5} luật khác.")
            else:
                print("CẢNH BÁO: Không tìm thấy luật hóa học chung nào.")
            print("------------------------------------------\n")

        except Exception as e:
            print(f"\n=======================================================")
            print(f"LỖI THIẾT LẬP CSDL HOẶC TẢI DỮ LIỆU: {e}")
            print(f"=======================================================\n")
            traceback.print_exc()


# ======================================================================
# API ENDPOINT: api_find_and_calculate_path (ĐÃ SỬA)
# ======================================================================

@app.route('/api/find_and_calculate_path', methods=['POST'])
def api_find_and_calculate_path():
    """
    API tìm chuỗi luật tính toán cho 1 chất duy nhất (đã tối ưu hóa).
    """
    data = request.get_json()
    print("\n[REQUEST NHẬN] Đã nhận yêu cầu /api/find_and_calculate_path")
    print(f"[DỮ LIỆU NHẬN] {json.dumps(data, indent=2)}")

    if not data or 'known_vars_with_values' not in data or 'target_var' not in data or 'substance_info' not in data:
        print("[LỖI] Thiếu dữ liệu trong request.")
        return jsonify({
            "success": False,
            "error": "Thiếu 'known_vars_with_values', 'target_var', hoặc 'substance_info' trong yêu cầu."
        }), 400

    known_vars_with_values: Dict[str, float] = data.get('known_vars_with_values', {})
    primary_formula: str = data.get('substance_info', '').strip()  # Đây là tên chất duy nhất
    target_var_type: str = data.get('target_var', '').strip()  # Đây là loại biến mục tiêu (VD: 'm')

    if not primary_formula or not target_var_type:
        return jsonify({"success": False, "error": "Chất hoặc Biến mục tiêu không hợp lệ."}), 400

    current_vars: Dict[str, float] = {}
    custom_rules = []

    try:
        molar_mass = get_molar_mass(primary_formula)

        # 1. Định nghĩa Tên biến đã Gán nhãn thực tế
        mass_var = f"m_{primary_formula}"
        mol_mass_var = f"M_{primary_formula}"
        mol_var = f"n_{primary_formula}"
        conc_var = f"C_{primary_formula}"

        # Nhãn biến mục tiêu cuối cùng
        target_var_labeled = f"{target_var_type}_{primary_formula}"

        # 2. Thêm Khối lượng Mol M_[Chất]
        current_vars[mol_mass_var] = molar_mass

        # 3. GÁN NHÃN các biến đầu vào (C, V, m) thành biến cụ thể
        for var_type, value in known_vars_with_values.items():
            if var_type == 'V':
                # Gán nhãn V thành V_dd
                current_vars['V_dd'] = value
            elif var_type == 'C':
                # Gán nhãn C thành C_[Chất]
                current_vars[conc_var] = value
            elif var_type == 'm':
                # Gán nhãn m thành m_[Chất]
                current_vars[mass_var] = value
            elif var_type == 'n':
                # Gán nhãn n thành n_[Chất]
                current_vars[mol_var] = value
            elif var_type == 'M':
                # Gán nhãn M thành M_[Chất] (M này sẽ ghi đè lên M tính toán nếu có)
                current_vars[mol_mass_var] = value

        # 4. TẠO CÁC LUẬT TÙY CHỈNH (Custom Rules)
        def create_custom_rule(name, formula, inputs, output, expression):
            return {
                'name': name, 'formula': formula, 'description': f'Luật tùy chỉnh cho {primary_formula}',
                'required_inputs': inputs, 'output_var': output, 'expression': expression
            }

        # Custom Rule 1: n = m / M
        custom_rules.append(create_custom_rule(
            f"Custom_n_tu_m_{primary_formula}", f"{mol_var} = {mass_var} / {mol_mass_var}",
            [mass_var, mol_mass_var], mol_var, f"{mass_var} / {mol_mass_var}"
        ))

        # Custom Rule 2: C = n / V_dd
        custom_rules.append(create_custom_rule(
            f"Custom_C_tu_n_{primary_formula}", f"{conc_var} = {mol_var} / V_dd",
            [mol_var, 'V_dd'], conc_var, f"{mol_var} / V_dd"
        ))

        # Custom Rule 3: n = C * V_dd
        custom_rules.append(create_custom_rule(
            f"Custom_n_tu_C_{primary_formula}", f"{mol_var} = {conc_var} * V_dd",
            [conc_var, 'V_dd'], mol_var, f"{conc_var} * V_dd"
        ))

        # Custom Rule 4: m = n * M
        custom_rules.append(create_custom_rule(
            f"Custom_m_tu_n_{primary_formula}", f"{mass_var} = {mol_var} * {mol_mass_var}",
            [mol_var, mol_mass_var], mass_var, f"{mol_var} * {mol_mass_var}"
        ))

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    known_vars_set = set(current_vars.keys())

    # Lấy luật chung từ CSDL
    all_rules_from_db = get_chemical_rules()

    # Thêm thuộc tính .to_dict() cho custom_rules
    for rule_dict in custom_rules:
        rule_dict['to_dict'] = lambda self=rule_dict: self

    all_rules_for_search = all_rules_from_db + custom_rules

    # === 5. Tìm kiếm đường đi (path) ===
    path_of_rules = find_calculation_path(known_vars_set, target_var_labeled, all_rules_for_search)

    if not path_of_rules:
        return jsonify({
            "success": False,
            "message": f"Không thể tìm thấy chuỗi luật nào để tính toán biến '{target_var_labeled}' từ các biến đã biết.",
            "initial_vars": list(known_vars_set)
        }), 404

    # === 6. Thực hiện tính toán theo chuỗi ===
    calculation_steps = []

    for i, rule_model_or_dict in enumerate(path_of_rules):
        try:
            rule_dict = rule_model_or_dict.to_dict() if hasattr(rule_model_or_dict, 'to_dict') else rule_model_or_dict

            expression = rule_dict['expression']
            output_var = rule_dict['output_var']

            result_value = execute_rule_expression(expression, current_vars)

            current_vars[output_var] = result_value

            step_detail = {
                "step": i + 1,
                "rule_name": rule_dict.get('name', 'N/A'),
                "formula": rule_dict.get('formula', 'N/A'),
                "expression_used": expression,
                "inputs_used_and_values": {var: current_vars[var] for var in rule_dict['required_inputs']},
                "output_var": output_var,
                "result_value": result_value
            }
            calculation_steps.append(step_detail)

            if output_var == target_var_labeled:
                break

        except ValueError as e:
            return jsonify({
                "success": False,
                "error": f"Lỗi tính toán ở bước {i + 1} ({rule_dict.get('name', 'N/A')}): {str(e)}",
                "path_so_far": calculation_steps
            }), 400

    # 7. Trả kết quả cuối cùng
    return jsonify({
        "success": True,
        "message": f"Đã tính toán thành công '{target_var_labeled}' sau {len(calculation_steps)} bước.",
        "target_var_labeled": target_var_labeled,
        "final_result": current_vars.get(target_var_labeled),
        "initial_inputs": known_vars_with_values,
        "calculation_path_details": calculation_steps
    })

# ... (Giữ nguyên các hàm api_forward_chaining, api_find_reaction_path, api_balance_equation, api_calculate_rule) ...
@app.route('/api/forward-chaining', methods=['POST'])
def api_forward_chaining():
    data = request.get_json()
    if not data or 'reactants' not in data:
        return jsonify({"success": False, "error": "Thiếu 'reactants' trong yêu cầu."}), 400

    reactants = data.get('reactants', '')
    conditions = data.get('conditions', '')

    try:
        # Giả định run_forward_chaining sử dụng get_reaction_rules() hoặc REACTION_RULES
        # (sau khi đã được load_reactions_from_db cập nhật)
        result = run_forward_chaining(reactants, conditions)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/find-reaction-path', methods=['POST'])
def api_find_reaction_path():
    data = request.get_json()
    if not data or 'reactants' not in data or 'target' not in data:
        return jsonify({"success": False, "error": "Thiếu 'reactants' hoặc 'target' trong yêu cầu."}), 400

    reactants = data.get('reactants', '')
    target = data.get('target', '')

    try:
        result = find_reaction_path(reactants, target)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/balance-equation', methods=['POST'])
def api_balance_equation():
    data = request.get_json()
    if not data or 'equation' not in data:
        return jsonify({"success": False, "error": "Thiếu 'equation' trong yêu cầu."}), 400

    equation_str = data.get('equation', '')

    try:
        result = balance_equation(equation_str)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/calculate_rule', methods=['POST'])
def api_calculate_rule():
    # Logic tính toán 1 bước đơn giản (giữ nguyên logic cũ)
    data = request.get_json()
    user_inputs: Dict[str, float] = data.get('inputs', {})
    print("test" + data)
    all_rules = get_chemical_rules()
    matched_rule = None

    for rule_model in all_rules:
        required_vars = rule_model.required_inputs
        if all(var in user_inputs for var in required_vars):
            matched_rule = rule_model
            break

    if not matched_rule:
        return jsonify({"success": False, "error": "Không tìm thấy luật phù hợp với các biến đầu vào đã cho."}), 404

    try:
        expression = matched_rule.expression
        output_var = matched_rule.output_var
        result_value = execute_rule_expression(expression, user_inputs)

        response_data = {
            "success": True,
            "rule_used": matched_rule.to_dict(),
            "output_var": output_var,
            "result": result_value
        }
        return jsonify(response_data)

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Lỗi không xác định trong tính toán: {str(e)}"}), 500


@app.route('/api/identify-chemicals', methods=['POST'])
def api_identify_chemicals():
    data = request.get_json()
    unknown_chemicals = data.get('chemicals', [])

    if not unknown_chemicals or len(unknown_chemicals) < 2:
        return jsonify({"success": False, "error": "Cung cấp ít nhất 2 chất cần nhận biết."}), 400

    try:
        identification_result = identify_chemicals(unknown_chemicals)

        return jsonify({"success": True, "data": identification_result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    setup_database(app)
    app.run(debug=True, host='0.0.0.0', port=5000)