from flask_sqlalchemy import SQLAlchemy
import json
from sqlalchemy.types import TypeDecorator, Text
from typing import List, Dict, Any

db = SQLAlchemy()


# Custom type cho việc lưu trữ List/Dict dưới dạng JSON trong CSDL
class JSONEncodedDict(TypeDecorator):
    """Lưu trữ Python dict/list dưới dạng JSON trong CSDL."""
    impl = Text  # Sử dụng kiểu Text (hoặc VARCHAR lớn) trong CSDL

    def process_bind_param(self, value, dialect):
        # Chuyển đổi từ Python object sang JSON string khi lưu vào DB
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        # Chuyển đổi từ JSON string sang Python object khi đọc từ DB
        if value is not None and value.strip():
            try:
                # Trả về list rỗng nếu chuỗi JSON là "[]"
                return json.loads(value)
            except json.JSONDecodeError:
                return []
        return []  # Trả về list rỗng nếu dữ liệu là None/Chuỗi rỗng


class ReactionModel(db.Model):
    __tablename__ = 'reactions'

    # CÁC TRƯỜNG DỮ LIỆU CSDL
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    reactants_json = db.Column(db.Text, nullable=False)
    products_json = db.Column(db.Text, nullable=False)
    conditions_json = db.Column(db.Text, nullable=True)
    equation_string = db.Column(db.String(255), nullable=True)

    # THUỘC TÍNH LOGIC (KHÔNG LƯU VÀO DB)
    # is_used dùng cho thuật toán tìm kiếm (forward-chaining)
    is_used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """
        Chuyển đổi ReactionModel sang dictionary, thực hiện giải mã (decode)
        chuỗi JSON thành Python list.
        """

        def safe_json_loads(json_string):
            if json_string is None or not json_string.strip():
                return []
            try:
                return json.loads(json_string)
            except json.JSONDecodeError:
                return []

        return {
            'id': self.id,
            'type': self.type,
            'description': self.description,
            'reactants': safe_json_loads(self.reactants_json),
            'products': safe_json_loads(self.products_json),
            'conditions': safe_json_loads(self.conditions_json),
            'equation_string': self.equation_string
        }

    # ==================================================================
    # CÁC PROPERTY TÍNH TOÁN DỰA TRÊN DỮ LIỆU CSDL (THAY THẾ CLASS Reaction)
    # ==================================================================

    @property
    def required_reactants(self) -> List[str]:
        """Trả về danh sách chất phản ứng (List Python)."""
        # Tải list từ JSON string
        return self.to_dict()['reactants']

    @property
    def products(self) -> List[str]:
        """Trả về danh sách sản phẩm (List Python)."""
        return self.to_dict()['products']

    @property
    def required_conditions(self) -> List[str]:
        """Trả về danh sách điều kiện (List Python)."""
        return self.to_dict()['conditions']

    def __repr__(self):
        # Tái định nghĩa repr để khớp với Reaction cũ, sử dụng các property mới
        reactants_str = " + ".join(self.required_reactants)
        products_str = " + ".join(self.products)
        conditions_str = f" [{', '.join(self.required_conditions)}]" if self.required_conditions else ""

        return (
            f"Loại: {self.type}\n"
            f"Mô tả: {self.description}\n"
            f"Phương trình: {reactants_str}({conditions_str}) -> {products_str}\n"
            f"Chất tham gia: {self.required_reactants}\n"
            f"Sản phẩm: {self.products}"
        )

    @staticmethod
    def from_reaction_object(reaction_obj: Any):
        # Giả định reaction_obj là một object có các thuộc tính:
        # type, description, required_reactants, required_conditions, products

        equation_str = f"{' + '.join(reaction_obj.required_reactants)} -> {' + '.join(reaction_obj.products)}"

        return ReactionModel(
            type=reaction_obj.type,
            description=reaction_obj.description,
            reactants_json=json.dumps(reaction_obj.required_reactants),
            products_json=json.dumps(reaction_obj.products),
            conditions_json=json.dumps(reaction_obj.required_conditions),
            equation_string=equation_str
        )


class ChemicalRuleModel(db.Model):
    __tablename__ = 'chemical_rules'  # Ánh xạ tới bảng chemical_rules

    # CÁC TRƯỜNG DỮ LIỆU CSDL
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    formula = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

    # Sử dụng JSONEncodedDict cho cột required_inputs (ví dụ: ["m", "M"])
    # Cột này sẽ được lưu dưới dạng chuỗi JSON và được tự động decode thành list/dict Python
    required_inputs = db.Column(JSONEncodedDict, nullable=False)

    output_var = db.Column(db.String(50), nullable=False)
    expression = db.Column(db.Text, nullable=False)

    # is_used: bool = False  # Không cần thiết cho luật tính toán/công thức

    def to_dict(self) -> Dict[str, Any]:
        """
        Chuyển đổi ChemicalRuleModel sang dictionary.
        Do required_inputs đã dùng JSONEncodedDict, nên nó đã là list Python.
        """
        return {
            'id': self.id,
            'name': self.name,
            'formula': self.formula,
            'description': self.description,
            # required_inputs đã là list/dict nhờ JSONEncodedDict
            'required_inputs': self.required_inputs,
            'output_var': self.output_var,
            'expression': self.expression
        }

    # ==================================================================
    # CÁC PROPERTY HỖ TRỢ (Tùy chọn)
    # ==================================================================

    @property
    def required_vars(self) -> List[str]:
        """Trả về danh sách các biến đầu vào cần thiết."""
        # required_inputs đã là list nhờ JSONEncodedDict
        return self.required_inputs

    def __repr__(self):
        inputs_str = ', '.join(self.required_inputs)
        return (
            f"<ChemicalRuleModel(id={self.id}, name='{self.name}', formula='{self.formula}', "
            f"inputs=[{inputs_str}], output='{self.output_var}')>"
        )

class ElementModel(db.Model):
    __tablename__ = 'elements'

    id = db.Column(db.Integer, primary_key=True)
    # Ký hiệu (Symbol) của nguyên tố, ví dụ: H, O, Fe
    mark = db.Column(db.String(10), nullable=False, unique=True)
    # Số thứ tự nguyên tử (Atomic Number)
    atomic_number = db.Column(db.Integer, nullable=False, unique=True)
    # Khối lượng nguyên tử (Atomic Mass)
    atomic_mass = db.Column(db.Float, nullable=False)
    # Hóa trị (Valence)
    valence = db.Column(db.Integer)

    def __repr__(self):
        return (
            f"<ElementModel(mark='{self.mark}', num={self.atomic_number}, mass={self.atomic_mass})>"
        )