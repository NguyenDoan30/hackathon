export type Accent = 'mint' | 'lavender' | 'peach' | 'blue';
export type ReviewRating = 'again' | 'hard' | 'good' | 'easy';
export type TutorMode = 'easy' | 'standard' | 'advanced';
export interface StudyDocument {
  id: string; name: string; size: number; mediaType: string;
  status: 'ready' | 'pending' | 'processing' | 'failed';
  transcript?: string; sourceMode: 'demo' | 'live';
}
export interface Lesson {
  id: string; title: string; description: string; topic: string; accent: Accent;
  createdAt: string; progress: number; documents: StudyDocument[];
}
export interface StudyNote { id: string; title: string; content: string; updatedAt: string }
export interface ChatMessage {
  id: string; role: 'user' | 'assistant'; content: string;
  sources?: {id: string; name: string}[];
}
export interface MindmapNode { id: string; title: string; description: string; children?: MindmapNode[] }
export interface Flashcard { id: string; question: string; answer: string; difficulty: 'easy' | 'medium' | 'hard' }
export interface QuizQuestion { id: string; question: string; options: string[]; answer: string; explanation: string }
export interface QuizResult {
  id: string; completedAt: string; scorePercentage: number; correctAnswers: number; totalQuestions: number;
  details: {questionId: string; selected: string; correct: string; isCorrect: boolean; explanation: string}[];
}
export interface LearningBundle {
  summary: {overview: string; keyPoints: string[]; takeaways: string[]};
  mindmap: MindmapNode[]; flashcards: Flashcard[]; quiz: {questions: QuizQuestion[]};
}
export interface DemoSnapshot {
  user: {name: string; email: string} | null; lessons: Lesson[]; notes: StudyNote[];
  chats: Record<string, ChatMessage[]>; reviews: Record<string, Record<string, ReviewRating>>;
  results: Record<string, QuizResult[]>;
}
