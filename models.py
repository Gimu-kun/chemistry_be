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