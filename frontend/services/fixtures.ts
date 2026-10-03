import type {DemoSnapshot, LearningBundle, Lesson, Accent} from '../types';

function bundle(id: string, title: string, overview: string, points: string[], questions: [string,string,string[]][]): LearningBundle {
  return {
    summary: {overview, keyPoints: points, takeaways: ['Giải thích các khái niệm bằng lời của bạn.', 'Tự kiểm tra kiến thức qua câu hỏi mẫu.']},
    mindmap: [{id: `${id}-root`, title, description: overview, children: points.map((point, i) => ({
      id: `${id}-node-${i}`, title: questions[i % questions.length][0], description: point}))}],
    flashcards: questions.map(([question, answer], i) => ({id: `${id}-card-${i}`, question, answer, difficulty: i ? 'medium' : 'easy'})),
    quiz: {questions: questions.map(([question, answer, others], i) => ({
      id: `${id}-quiz-${i}`, question, options: i % 2 ? [others[0], answer, ...others.slice(1)] : [answer, ...others],
      answer, explanation: points[i % points.length]}))},
  };
}

export const learningFixtures: Record<string, LearningBundle> = {
  'sample-database': bundle('database', 'Cơ sở dữ liệu',
    'Cơ sở dữ liệu lưu thông tin có tổ chức. Hệ quản trị giúp tạo, cập nhật và truy vấn thông tin; SQLite là một ví dụ.',
    ['Cơ sở dữ liệu là tập hợp dữ liệu có liên quan, được tổ chức để sử dụng.',
     'Hệ quản trị cơ sở dữ liệu là phần mềm quản lý và truy vấn dữ liệu.',
     'SQLite là hệ quản trị nhúng, thường lưu một cơ sở dữ liệu trong một tệp.'],
    [['Cơ sở dữ liệu là gì?', 'Tập hợp dữ liệu có tổ chức', ['Một màn hình', 'Một loại bàn phím', 'Một bản nhạc']],
     ['Hệ quản trị cơ sở dữ liệu làm gì?', 'Quản lý và truy vấn dữ liệu', ['Chỉ vẽ ảnh', 'Chỉ phát âm thanh', 'Thay hệ điều hành']],
     ['SQLite thuộc nhóm nào?', 'Hệ quản trị cơ sở dữ liệu', ['Trình chỉnh ảnh', 'Thiết bị lưu điện', 'Ngôn ngữ đánh dấu']]]),
  'sample-probability': bundle('probability', 'Xác suất cơ bản',
    'Xác suất mô tả khả năng xảy ra của một biến cố. Với các kết quả đồng khả năng, xác suất bằng số kết quả thuận lợi chia tổng số kết quả.',
    ['Xác suất nằm trong đoạn từ 0 đến 1.', 'Biến cố chắc chắn có xác suất bằng 1.', 'Tung đồng xu cân đối một lần: xác suất ra mặt ngửa là 1/2.'],
    [['Xác suất thuộc khoảng nào?', 'Từ 0 đến 1', ['Từ 2 đến 3', 'Luôn âm', 'Luôn lớn hơn 1']],
     ['Biến cố chắc chắn có xác suất bao nhiêu?', '1', ['0', '-1', '2']],
     ['Đồng xu cân đối có xác suất ra ngửa bao nhiêu?', '1/2', ['1/3', '1/4', '1']]]),
  'sample-biology': bundle('biology', 'Quang hợp',
    'Quang hợp chuyển năng lượng ánh sáng thành năng lượng hóa học. Cây sử dụng nước và carbon dioxide để tổng hợp chất hữu cơ.',
    ['Ánh sáng cung cấp năng lượng cho quá trình quang hợp.', 'Nước và carbon dioxide là các nguyên liệu của quang hợp.', 'Quang hợp ở thực vật giải phóng oxygen.'],
    [['Nguồn năng lượng của quang hợp là gì?', 'Ánh sáng', ['Âm thanh', 'Sóng radio', 'Lực ma sát']],
     ['Quang hợp sử dụng khí nào?', 'Carbon dioxide', ['Helium', 'Neon', 'Hydrogen']],
     ['Quang hợp ở thực vật giải phóng khí nào?', 'Oxygen', ['Helium', 'Neon', 'Methane']]]),
};

export const genericFixture = bundle('practice', 'Phương pháp học — nội dung mẫu',
  'Đây là nội dung minh họa cách học chủ động, không được tạo từ tài liệu của bài học mới. Hãy thử tóm tắt, tự hỏi và ôn lại.',
  ['Đọc một phần ngắn rồi tóm tắt bằng lời của bạn.', 'Tự trả lời câu hỏi trước khi xem đáp án.', 'Ôn lại những phần chưa nhớ.'],
  [['Sau khi đọc, bạn nên làm gì?', 'Tóm tắt bằng lời của mình', ['Bỏ qua ý chính', 'Chép không đọc', 'Đóng bài ngay']],
   ['Dùng flashcard thế nào?', 'Tự trả lời trước khi lật thẻ', ['Luôn mở sẵn đáp án', 'Không đọc câu hỏi', 'Chỉ đếm thẻ']],
   ['Khi trả lời sai, nên làm gì?', 'Xem lại giải thích và ôn tập', ['Bỏ học', 'Xóa mọi ghi chú', 'Không xem đáp án']]]);

export function initialSnapshot(): DemoSnapshot {
  const seeds: [string,string,string,Accent][] = [
    ['sample-database','Cơ sở dữ liệu & SQLite','Công nghệ thông tin','mint'],
    ['sample-probability','Những bước đầu với xác suất','Toán học','lavender'],
    ['sample-biology','Khám phá quá trình quang hợp','Sinh học','peach'],
  ];
  const lessons: Lesson[] = seeds.map(([id,title,topic,accent]) => ({
    id,title,topic,accent,description:learningFixtures[id].summary.overview,
    createdAt:'2026-10-03T00:00:00.000Z',progress:0,
    documents:[{id:`${id}-document`,name:`${title} — tài liệu mẫu.txt`,size:1024,mediaType:'text/plain',
      status:'ready',sourceMode:'demo',transcript:learningFixtures[id].summary.keyPoints.join('\n\n')}],
  }));
  return {user:null,lessons,notes:[],chats:{},reviews:{},results:{}};
}
