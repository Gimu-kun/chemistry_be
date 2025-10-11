from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from urllib.parse import quote_plus

# Import models để có thể truyền nó vào load_reactions_from_db
import models

# !!! CẬP NHẬT: Import thêm hàm get_reaction_rules !!!
from chemistry_data import load_reactions_from_db, get_reaction_rules

# Import cần thiết từ models
from models import db, ReactionModel

# Giả định các module này đã được định nghĩa
from forward_chaining import run_forward_chaining
from reaction_path import find_reaction_path
from balancer import balance_equation

app = Flask(__name__)
CORS(app)

# ======================================================================
# CẤU HÌNH CSDL
# ======================================================================

DB_USER = 'root'
DB_PASSWORD_ENCODED = quote_plus('June1996@')
DB_HOST = '127.0.0.1'
DB_NAME = 'chemistry'

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD_ENCODED}@{DB_HOST}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


# ======================================================================
# HÀM SETUP CSDL VÀ TẢI DỮ LIỆU VÀO BỘ NHỚ (SETUP_DATABASE)
# ======================================================================

def setup_database(app):
    """
    Thiết lập CSDL (tạo bảng nếu chưa có) và tải luật phản ứng vào bộ nhớ.
    """
    with app.app_context():
        try:
            db.create_all()
            print("Đã kiểm tra và đảm bảo các bảng CSDL đã tồn tại.")

            # TẢI DỮ LIỆU TỪ CSDL VÀO BIẾN REACTION_RULES
            load_reactions_from_db(models)

            # =================================================
            #           LOG RA ĐỂ KIỂM TRA DỮ LIỆU
            # Sử dụng get_reaction_rules() để lấy dữ liệu MỚI NHẤT
            # =================================================
            print("\n--- DANH SÁCH PHẢN ỨNG ĐÃ TẢI TỪ CSDL ---")

            # !!! SỬ DỤNG HÀM GETTER !!!
            current_rules = get_reaction_rules()

            if current_rules:
                print(current_rules[0])
                # In ra chi tiết 5 phản ứng đầu tiên và tổng số
                for i, reaction in enumerate(current_rules[:5]):
                    reactants_str = ' + '.join(reaction.required_reactants)
                    products_str = ' + '.join(reaction.products)
                    print(f"[{i + 1}] {reaction.type}: {reactants_str} -> {products_str}")

                if len(current_rules) > 5:
                    print(f"  ... và {len(current_rules) - 5} phản ứng khác. Tổng cộng: {len(current_rules)}.")
            else:
                print("Không tìm thấy phản ứng nào trong CSDL.")
            print("------------------------------------------\n")
            # =================================================

        except Exception as e:
            print(f"LỖI THIẾT LẬP CSDL HOẶC TẢI DỮ LIỆU: {e}")


# ======================================================================
# API ENDPOINTS (GIỮ NGUYÊN)
# ======================================================================

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


# Khởi chạy ứng dụng
if __name__ == '__main__':
    setup_database(app)
    app.run(debug=True, host='0.0.0.0', port=5000)