"""Deterministic demo fixtures, NEVER selected in production mode.

These fixtures demonstrate the backend contract, not RAG/OCR/AI capabilities.
"""
from pathlib import Path

DEMO_TEXT = '''Lập trình hướng đối tượng (OOP)
Class là bản thiết kế, object là một thể hiện cụ thể của class.
Encapsulation (đóng gói) gom dữ liệu và phương thức, kiểm soát quyền truy cập.
Inheritance (kế thừa) giúp lớp con tái sử dụng đặc điểm của lớp cha.
Polymorphism (đa hình) cho phép cùng một giao diện có nhiều cách thực thi.
Ví dụ: Dog và Cat cùng có phương thức speak(), nhưng phát ra âm thanh khác nhau.
'''

class DemoFile:
    def process(self, path: Path, media_type: str):
        if path.suffix.lower() in ('.txt', '.md'):
            content = path.read_text(encoding='utf-8-sig')
            return {'content': content, 'transcript': None}
        audio = media_type.startswith('audio/')
        text = '[MÔ PHỎNG: nội dung mẫu OOP, chưa trích xuất từ file này]\n' + DEMO_TEXT
        return {'content': text, 'transcript': text if audio else None}

class DemoAI:
    def summarize(self, documents):
        return {'summary': 'Bản tóm tắt mẫu: OOP tổ chức chương trình bằng class và object. Ba khái niệm cần ôn là đóng gói, kế thừa và đa hình.',
                'key_points': ['Class là bản thiết kế; object là thể hiện cụ thể.', 'Đóng gói kiểm soát quyền truy cập dữ liệu.', 'Kế thừa tái sử dụng hành vi.', 'Đa hình: cùng giao diện, nhiều cách thực thi.']}
    def chat(self, question, documents, history):
        return {'answer': 'Đây là phản hồi mô phỏng để kiểm tra API và lưu lịch sử. Ví dụ mẫu về đa hình: Dog và Cat cùng có speak(), nhưng mỗi lớp thực thi khác nhau. Module AI/RAG của Người 3 sẽ cung cấp câu trả lời thật theo tài liệu.',
                'sources': [documents[0]['id']]}

class DemoLearning:
    def flashcards(self, documents):
        return [
            {'question': 'Class và object khác nhau thế nào?', 'answer': 'Class là bản thiết kế; object là thể hiện cụ thể.', 'difficulty': 'easy'},
            {'question': 'Đóng gói có tác dụng gì?', 'answer': 'Gom dữ liệu và hành vi, kiểm soát quyền truy cập.', 'difficulty': 'medium'},
            {'question': 'Đa hình là gì?', 'answer': 'Cùng một giao diện có nhiều cách thực thi.', 'difficulty': 'medium'},
            {'question': 'Kế thừa giúp ích gì?', 'answer': 'Lớp con tái sử dụng và mở rộng hành vi lớp cha.', 'difficulty': 'easy'}]
    def quiz(self, documents):
        return [
            {'id': 'q1', 'question': 'Object là gì?', 'options': ['Một thể hiện của class', 'Một kiểu database', 'Một giao thức mạng'], 'answer': 'Một thể hiện của class', 'explanation': 'Object là một thể hiện cụ thể được tạo từ class.'},
            {'id': 'q2', 'question': 'Khái niệm nào kiểm soát quyền truy cập dữ liệu?', 'options': ['Kế thừa', 'Đóng gói', 'Đa hình'], 'answer': 'Đóng gói', 'explanation': 'Đóng gói kết hợp dữ liệu và hành vi với quyền truy cập phù hợp.'},
            {'id': 'q3', 'question': 'Dog và Cat thực thi speak() khác nhau là ví dụ của?', 'options': ['Đa hình', 'Phân trang', 'Transaction'], 'answer': 'Đa hình', 'explanation': 'Cùng một giao diện speak() có nhiều cách thực thi.'}]
    def grade(self, questions, answers):
        feedback = [{'question_id': q['id'], 'correct': answers.get(q['id']) == q['answer'], 'answer': q['answer'], 'explanation': q['explanation']} for q in questions]
        correct = sum(f['correct'] for f in feedback)
        return {'correct': correct, 'total': len(questions), 'score': round(100 * correct / len(questions), 2), 'feedback': feedback}
