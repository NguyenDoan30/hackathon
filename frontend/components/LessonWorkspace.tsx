"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import type { DemoSnapshot, Lesson, MindmapNode, QuizResult, ReviewRating, TutorMode } from "../types";
import { demoChat, demoQuiz, getLearningBundle, uid } from "../services/demo";
import { Icon } from "./Icon";
import "./LessonWorkspace.css";

type Tab = "summary" | "chat" | "mindmap" | "flashcards" | "quiz" | "documents";
interface Props {
  lesson: Lesson;
  snapshot: DemoSnapshot;
  onChange: (snapshot: DemoSnapshot) => void;
  onBack: () => void;
  onUpload: () => void;
  notify: (text: string) => void;
  initialTab?: Tab;
}

const tabs: { id: Tab; label: string; icon: string }[] = [
  { id: "summary", label: "Tổng quan", icon: "book" },
  { id: "chat", label: "AI Tutor", icon: "chat" },
  { id: "mindmap", label: "Sơ đồ tư duy", icon: "brain" },
  { id: "flashcards", label: "Flashcard", icon: "cards" },
  { id: "quiz", label: "Quiz", icon: "quiz" },
  { id: "documents", label: "Tài liệu", icon: "file" },
];
const tutorModes: { id: TutorMode; label: string; detail: string }[] = [
  { id: "easy", label: "Dễ hiểu", detail: "Bắt đầu từ những điều quen thuộc" },
  { id: "standard", label: "Tiêu chuẩn", detail: "Nắm khái niệm và cách áp dụng" },
  { id: "advanced", label: "Chuyên sâu", detail: "Phân tích kỹ hơn, kết nối kiến thức" },
];
const ratings: { id: ReviewRating; label: string; icon: string }[] = [
  { id: "again", label: "Học lại", icon: "refresh" },
  { id: "hard", label: "Hơi khó", icon: "brain" },
  { id: "good", label: "Đã nhớ", icon: "check" },
  { id: "easy", label: "Rất dễ", icon: "sparkles" },
];
const difficultyLabels = { easy: "Cơ bản", medium: "Vừa sức", hard: "Nâng cao" };
const statusLabels = { ready: "Sẵn sàng", pending: "Đang chờ", processing: "Đang xử lý", failed: "Cần thử lại" };
const formatSize = (size: number) => size >= 1048576 ? `${(size / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(size / 1024))} KB`;
const isSavedNote = (document: Lesson["documents"][number]) => document.mediaType === "text/plain" && document.name === "Ghi chú bài học";

function mapLayout(roots: MindmapNode[]) {
  const nodes: { node: MindmapNode; x: number; y: number }[] = [];
  const edges: { from: { x: number; y: number }; to: { x: number; y: number } }[] = [];
  let row = 0;
  let depthMax = 0;
  function walk(node: MindmapNode, depth: number): { x: number; y: number } {
    depthMax = Math.max(depthMax, depth);
    const children = (node.children ?? []).map(child => walk(child, depth + 1));
    const y = children.length ? children.reduce((total, child) => total + child.y, 0) / children.length : 32 + row++ * 108;
    const position = { x: 32 + depth * 286, y };
    nodes.push({ node, ...position });
    children.forEach(child => edges.push({ from: position, to: child }));
    return position;
  }
  roots.forEach(root => { walk(root, 0); row += 0.5; });
  return { nodes, edges, width: Math.max(810, depthMax * 286 + 300), height: Math.max(390, row * 108 + 64) };
}

export default function LessonWorkspace({ lesson, snapshot, onChange, onBack, onUpload, notify, initialTab = "summary" }: Props) {
  const [tab, setTab] = useState<Tab>(initialTab);
  const [tutorMode, setTutorMode] = useState<TutorMode>("easy");
  const [question, setQuestion] = useState("");
  const [chatPending, setChatPending] = useState(false);
  const [chatError, setChatError] = useState("");
  const [cardIndex, setCardIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [quizResult, setQuizResult] = useState<QuizResult | null>(() => snapshot.results[lesson.id]?.slice(-1)[0] ?? null);
  const [quizPending, setQuizPending] = useState(false);
  const [quizError, setQuizError] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const [zoom, setZoom] = useState(1);
  const [selectedDocumentId, setSelectedDocumentId] = useState(lesson.documents[0]?.id ?? "");
  const latestSnapshot = useRef(snapshot);
  const activeLesson = useRef(lesson.id);
  const chatEnd = useRef<HTMLDivElement>(null);
  const chatInput = useRef<HTMLTextAreaElement>(null);
  const quizContainer = useRef<HTMLDivElement>(null);
  latestSnapshot.current = snapshot;

  const bundle = useMemo(() => getLearningBundle(lesson), [lesson]);
  const graph = useMemo(() => mapLayout(bundle.mindmap), [bundle.mindmap]);
  const selectedNode = graph.nodes.find(item => item.node.id === selectedNodeId)?.node ?? bundle.mindmap[0];
  const messages = snapshot.chats[lesson.id] ?? [];
  const reviews = snapshot.reviews[lesson.id] ?? {};
  const card = bundle.flashcards[cardIndex];
  const answeredCount = Object.keys(answers).length;
  const reviewedCount = bundle.flashcards.filter(item => reviews[item.id]).length;
  const selectedDocument = lesson.documents.find(item => item.id === selectedDocumentId) ?? lesson.documents[0];

  useEffect(() => { setTab(initialTab); }, [initialTab, lesson.id]);
  useEffect(() => {
    activeLesson.current = lesson.id;
    setQuestion(""); setChatPending(false); setChatError("");
    setCardIndex(0); setFlipped(false); setAnswers({}); setQuizError(""); setQuizPending(false);
    setQuizResult(latestSnapshot.current.results[lesson.id]?.slice(-1)[0] ?? null);
    setSelectedNodeId(""); setZoom(1); setSelectedDocumentId(lesson.documents[0]?.id ?? "");
    return () => { activeLesson.current = ""; };
  }, [lesson.id]);
  useEffect(() => {
    if (tab === "chat") chatEnd.current?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "nearest" });
  }, [messages.length, chatPending, tab]);

  useEffect(() => {
    if (quizResult && tab === "quiz") quizContainer.current?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
  }, [quizResult, tab]);

  async function sendQuestion(input = question) {
    const trimmed = input.trim();
    if (!trimmed || chatPending) return;
    const currentLessonId = lesson.id;
    const userMessage = { id: uid("message"), role: "user" as const, content: trimmed };
    const current = latestSnapshot.current;
    const next = { ...current, chats: { ...current.chats, [lesson.id]: [...(current.chats[lesson.id] ?? []), userMessage] } };
    latestSnapshot.current = next;
    onChange(next);
    setQuestion(""); setChatPending(true); setChatError("");
    try {
      const response = await demoChat(lesson, trimmed, tutorMode);
      if (activeLesson.current !== currentLessonId) return;
      const current = latestSnapshot.current;
      const next = { ...current, chats: { ...current.chats, [lesson.id]: [...(current.chats[lesson.id] ?? []), response] } };
      latestSnapshot.current = next;
      onChange(next);
    } catch (error) {
      if (activeLesson.current === currentLessonId) {
        const message = error instanceof Error ? error.message : "Không xác định được lỗi.";
        setChatError(`AI Tutor chưa trả lời được: ${message}`);
        setQuestion(trimmed);
      }
    } finally {
      if (activeLesson.current === currentLessonId) { setChatPending(false); chatInput.current?.focus(); }
    }
  }

  function reviewCard(rating: ReviewRating) {
    if (!card) return;
    const current = latestSnapshot.current;
    onChange({ ...current, reviews: { ...current.reviews, [lesson.id]: { ...(current.reviews[lesson.id] ?? {}), [card.id]: rating } } });
    notify(`Đã lưu: ${ratings.find(item => item.id === rating)?.label}.`);
    if (cardIndex < bundle.flashcards.length - 1) { setCardIndex(index => index + 1); setFlipped(false); }
  }

  async function submitQuiz() {
    if (quizPending) return;
    if (answeredCount !== bundle.quiz.questions.length) {
      setQuizError("Chọn một đáp án cho từng câu trước khi nộp bài.");
      const missing = bundle.quiz.questions.find(item => !answers[item.id]);
      if (missing) Array.from(quizContainer.current?.querySelectorAll<HTMLFieldSetElement>("[data-question]") ?? []).find(element => element.dataset.question === missing.id)?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" });
      return;
    }
    const currentLessonId = lesson.id;
    setQuizPending(true); setQuizError("");
    try {
      const result = await demoQuiz(lesson, answers);
      if (activeLesson.current !== currentLessonId) return;
      setQuizResult(result);
      const current = latestSnapshot.current;
      onChange({ ...current, results: { ...current.results, [lesson.id]: [...(current.results[lesson.id] ?? []), result] } });
      notify("Đã lưu kết quả quiz mẫu vào tiến độ của bạn.");
    } catch {
      if (activeLesson.current === currentLessonId) setQuizError("Chưa chấm được bài mẫu. Đáp án đã chọn được giữ lại để thử lại.");
    } finally {
      if (activeLesson.current === currentLessonId) setQuizPending(false);
    }
  }

  function switchCard(direction: number) {
    setCardIndex(index => Math.max(0, Math.min(bundle.flashcards.length - 1, index + direction)));
    setFlipped(false);
  }

  return (
    <div className="lw-workspace">
      <button type="button" className="btn btn-ghost lw-back" onClick={onBack}><Icon name="arrowLeft" size={17} /> Thư viện bài học</button>
      <header className="lw-heading">
        <div>
          <div className="lw-heading-meta"><span className={`badge lw-topic lw-topic-${lesson.accent}`}>{lesson.topic}</span><span className="lw-demo-label"><span /> Nội dung demo</span></div>
          <h1>{lesson.title}</h1>
          <p>{lesson.description || "Không gian học tập của bạn. Biến từng ý nhỏ thành kiến thức vững vàng."}</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={onUpload}><Icon name="plus" size={18} /> Thêm tài liệu</button>
      </header>
      <nav className="lw-tabs" role="tablist" aria-label="Công cụ học tập" onKeyDown={event => {
        if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
        event.preventDefault();
        const index = tabs.findIndex(item => item.id === tab);
        const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
        setTab(tabs[next].id);
        event.currentTarget.querySelectorAll<HTMLButtonElement>("button")[next]?.focus();
      }}>
        {tabs.map(item => <button type="button" key={item.id} id={`lw-tab-${item.id}`} role="tab" aria-selected={tab === item.id} aria-controls={`lw-panel-${item.id}`} tabIndex={tab === item.id ? 0 : -1} className={tab === item.id ? "lw-tab active" : "lw-tab"} onClick={() => setTab(item.id)}><Icon name={item.icon} size={18} />{item.label}{item.id === "documents" && <span className="lw-tab-count">{lesson.documents.length}</span>}</button>)}
      </nav>
      <div role="tabpanel" id={`lw-panel-${tab}`} aria-labelledby={`lw-tab-${tab}`} className="lw-content">
        {tab === "summary" && <div className="lw-overview-grid">
          <main className="lw-overview-main">
            <section className="panel lw-summary-card">
              <div className="lw-section-header"><div className="lw-icon-square"><Icon name="sparkles" size={21} /></div><div><span className="eyebrow">BỨC TRANH TỔNG THỂ</span><h2>Tóm tắt bài học</h2></div><span className="lw-soft-badge">Nội dung mẫu</span></div>
              <p className="lw-summary-text">{bundle.summary.overview}</p>
              <div className="lw-summary-notice"><Icon name="file" size={16} /><span>Bản mẫu giúp bạn trải nghiệm giao diện. Tệp được chọn trong demo chưa được AI đọc hoặc phân tích.</span></div>
              <div className="lw-summary-bottom"><span><span className="lw-small-dot" /> Sẵn sàng để bắt đầu học</span><button type="button" className="lw-text-button" onClick={() => setTab("chat")}>Hỏi AI Tutor <Icon name="arrowRight" size={16} /></button></div>
            </section>
            <section className="panel lw-keypoints"><div className="lw-card-heading"><h2>Những ý chính cần nhớ</h2><span className="muted">{bundle.summary.keyPoints.length} ý chính</span></div><ol>{bundle.summary.keyPoints.map((point, index) => <li key={index}><span>{String(index + 1).padStart(2, "0")}</span><p>{point}</p></li>)}</ol></section>
            <section className="lw-tools-grid">
              <button type="button" className="lw-tool-card lw-tool-lavender" onClick={() => setTab("mindmap")}><Icon name="brain" size={23} /><strong>Kết nối kiến thức</strong><span>Nhìn bài học qua sơ đồ tư duy</span><Icon name="arrowRight" size={18} /></button>
              <button type="button" className="lw-tool-card lw-tool-peach" onClick={() => setTab("quiz")}><Icon name="quiz" size={23} /><strong>Thử sức một chút</strong><span>Kiểm tra điều bạn vừa học</span><Icon name="arrowRight" size={18} /></button>
            </section>
          </main>
          <aside className="lw-overview-aside">
            <section className="panel lw-takeaways"><span className="eyebrow">MANG THEO SAU BÀI HỌC</span><h2>Học xong, bạn sẽ…</h2><ul>{bundle.summary.takeaways.map((point, index) => <li key={index}><span className="lw-check-circle"><Icon name="check" size={13} /></span><span>{point}</span></li>)}</ul></section>
            <section className="lw-review-invite"><span className="lw-invite-icon"><Icon name="cards" size={28} /></span><span className="eyebrow">MỖI NGÀY MỘT CHÚT</span><h3>Nhớ lâu hơn,<br />học nhẹ nhàng hơn.</h3><p>{bundle.flashcards.length} thẻ kiến thức mẫu đang chờ bạn khám phá.</p><button type="button" className="btn btn-secondary" onClick={() => setTab("flashcards")}>Ôn với flashcard <Icon name="arrowRight" size={16} /></button></section>
          </aside>
        </div>}

        {tab === "chat" && <div className="lw-tutor-grid">
          <aside className="panel lw-tutor-options"><div className="lw-icon-square"><Icon name="sparkles" size={22} /></div><h2>Học theo cách của bạn</h2><p className="muted">Chọn cách giải thích phù hợp với nhịp học của mình.</p><div className="lw-mode-options" role="radiogroup" aria-label="Mức độ giải thích">{tutorModes.map(mode => <button type="button" key={mode.id} aria-pressed={tutorMode === mode.id} disabled={chatPending} className={`lw-mode ${tutorMode === mode.id ? "selected" : ""}`} onClick={() => setTutorMode(mode.id)}><span className="lw-radio-dot" /><span><strong>{mode.label}</strong><small>{mode.detail}</small></span></button>)}</div><div className="lw-tutor-tip"><span className="eyebrow">MỘT GỢI Ý NHỎ</span><p>Hỏi cụ thể một khái niệm, sau đó thử diễn đạt lại bằng lời của bạn.</p></div><p className="lw-fixture-caption">AI Tutor sử dụng Gemini. API key chỉ được giữ trong tab trình duyệt hiện tại.</p></aside>
          <section className="panel lw-chat-panel"><div className="lw-chat-heading"><div className="lw-chat-avatar"><Icon name="sparkles" size={20} /></div><div><h2>AI Tutor</h2><p>Không gian để hỏi, hiểu và khám phá</p></div><span className="lw-soft-badge">Gemini AI</span></div><div className="lw-chat-scroll" aria-live="polite" aria-relevant="additions text">
            {!messages.length && <div className="lw-chat-welcome"><div className="lw-welcome-mark"><Icon name="sparkles" size={29} /></div><h3>Điều gì đang khiến bạn tò mò?</h3><p>Mình cùng đi qua bài học từng chút một.<br />Chọn một gợi ý hoặc viết câu hỏi của bạn.</p><div className="lw-suggestions">{["Giải thích bài này thật dễ hiểu", "Cho mình một ví dụ thực tế", "Mình cần nhớ những ý nào?"].map(prompt => <button type="button" key={prompt} disabled={chatPending} onClick={() => void sendQuestion(prompt)}>{prompt}<Icon name="arrowRight" size={15} /></button>)}</div></div>}
            {messages.map(message => <article key={message.id} className={`lw-message lw-message-${message.role}`}>{message.role === "assistant" && <div className="lw-message-avatar"><Icon name="sparkles" size={16} /></div>}<div className="lw-message-body"><span className="lw-message-author">{message.role === "assistant" ? "AI Tutor" : "Bạn"}</span><p>{message.content}</p>{!!message.sources?.length && <div className="lw-message-sources"><span>Nguồn:</span>{message.sources.map(source => <button type="button" key={source.id} onClick={() => { setSelectedDocumentId(source.id); setTab("documents"); }}><Icon name="file" size={13} />{source.name}</button>)}</div>}</div></article>)}
            {chatPending && <div className="lw-message lw-message-assistant"><div className="lw-message-avatar"><Icon name="sparkles" size={16} /></div><div className="lw-typing" role="status"><span /><span /><span /><small>AI đang suy nghĩ…</small></div></div>}<div ref={chatEnd} />
          </div><form className="lw-chat-form" onSubmit={event => { event.preventDefault(); void sendQuestion(); }}>{chatError && <p className="lw-error" role="alert">{chatError}</p>}<label htmlFor="lw-question" className="lw-visually-hidden">Câu hỏi cho AI Tutor</label><div className="lw-compose"><textarea ref={chatInput} id="lw-question" value={question} onChange={event => setQuestion(event.target.value)} maxLength={4000} placeholder="Hỏi về bài học của bạn…" rows={2} disabled={chatPending} onKeyDown={event => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void sendQuestion(); } }} /><button type="submit" className="lw-send-button" disabled={!question.trim() || chatPending} aria-label="Gửi câu hỏi">{chatPending ? <span className="spinner" /> : <Icon name="arrowRight" size={21} />}</button></div><div className="lw-compose-caption"><span>Enter để gửi · Shift + Enter để xuống dòng</span><span>{question.length}/4000</span></div></form></section>
        </div>}

        {tab === "mindmap" && <section className="panel lw-mindmap"><div className="lw-card-heading"><div><span className="eyebrow">THẤY ĐƯỢC SỰ KẾT NỐI</span><h2>Sơ đồ tư duy</h2><p className="muted">Chọn một nhánh để khám phá nội dung. Đây là sơ đồ mẫu.</p></div><div className="lw-zoom-controls"><button type="button" aria-label="Thu nhỏ sơ đồ" disabled={zoom <= 0.6} onClick={() => setZoom(value => Math.max(0.6, Math.round((value - 0.1) * 10) / 10))}><Icon name="zoomOut" size={18} /></button><button type="button" title="Đưa về kích thước ban đầu" onClick={() => setZoom(1)}>{Math.round(zoom * 100)}%</button><button type="button" aria-label="Phóng to sơ đồ" disabled={zoom >= 1.5} onClick={() => setZoom(value => Math.min(1.5, Math.round((value + 0.1) * 10) / 10))}><Icon name="zoomIn" size={18} /></button></div></div><div className="lw-map-scroll" tabIndex={0} role="region" aria-label="Sơ đồ có thể cuộn ngang và dọc"><div style={{ width: graph.width * zoom, height: graph.height * zoom }}><div className="lw-map-canvas" style={{ width: graph.width, height: graph.height, transform: `scale(${zoom})` }}><svg className="lw-map-lines" width={graph.width} height={graph.height} aria-hidden="true">{graph.edges.map((edge, index) => <path key={index} d={`M ${edge.from.x + 222} ${edge.from.y + 35} C ${edge.from.x + 256} ${edge.from.y + 35}, ${edge.to.x - 34} ${edge.to.y + 35}, ${edge.to.x} ${edge.to.y + 35}`} />)}</svg>{graph.nodes.map((item, index) => <button type="button" key={item.node.id} className={`lw-map-node lw-map-color-${index % 4} ${selectedNode?.id === item.node.id ? "selected" : ""}`} style={{ left: item.x, top: item.y }} aria-pressed={selectedNode?.id === item.node.id} onClick={() => setSelectedNodeId(item.node.id)}><span className="lw-map-node-dot" /><strong>{item.node.title}</strong>{!!item.node.children?.length && <span className="lw-map-children">{item.node.children.length}</span>}</button>)}</div></div></div>{selectedNode && <div className="lw-node-detail"><span className="lw-icon-square"><Icon name="brain" size={21} /></span><div><span className="eyebrow">NHÁNH BẠN ĐANG XEM</span><h3>{selectedNode.title}</h3><p>{selectedNode.description}</p></div></div>}<div className="lw-map-footer"><span><span className="lw-small-dot" /> Sơ đồ nội dung mẫu</span><span>Dùng nút + / − để đổi kích thước, cuộn để xem các nhánh.</span></div></section>}

        {tab === "flashcards" && <section className="panel lw-flashcards"><div className="lw-card-heading"><div><span className="eyebrow">NHỚ TỪNG CHÚT MỘT</span><h2>Ôn tập với flashcard</h2><p className="muted">Thử nhớ câu trả lời trước khi lật thẻ.</p></div><span className="lw-soft-badge">Bộ thẻ mẫu</span></div>{card ? <><div className="lw-card-progress"><span>{reviewedCount} / {bundle.flashcards.length} thẻ đã đánh giá</span><div><span style={{ width: `${reviewedCount / bundle.flashcards.length * 100}%` }} /></div></div><div className="lw-flashcard-stage"><button type="button" className={`lw-flashcard ${flipped ? "flipped" : ""}`} onClick={() => setFlipped(value => !value)} aria-label={flipped ? card.answer : card.question} aria-pressed={flipped}><div className="lw-flashcard-face lw-flashcard-front" aria-hidden={flipped}><div className="lw-flashcard-top"><span className="lw-soft-badge">{difficultyLabels[card.difficulty]}</span><span>{String(cardIndex + 1).padStart(2, "0")} / {String(bundle.flashcards.length).padStart(2, "0")}</span></div><span className="eyebrow">CÂU HỎI</span><h3>{card.question}</h3><span className="lw-flip-hint"><Icon name="refresh" size={16} /> Bấm vào thẻ để xem đáp án</span></div><div className="lw-flashcard-face lw-flashcard-back" aria-hidden={!flipped}><div className="lw-flashcard-top"><span className="lw-soft-badge">Đáp án mẫu</span><Icon name="check" size={20} /></div><span className="eyebrow">LỜI GIẢI</span><p>{card.answer}</p><span className="lw-flip-hint"><Icon name="refresh" size={16} /> Bấm để xem lại câu hỏi</span></div></button></div><div className="lw-card-navigation"><button type="button" className="btn btn-ghost" disabled={cardIndex === 0} onClick={() => switchCard(-1)}><Icon name="chevronLeft" size={18} /> Thẻ trước</button><span>{cardIndex + 1} / {bundle.flashcards.length}</span><button type="button" className="btn btn-ghost" disabled={cardIndex === bundle.flashcards.length - 1} onClick={() => switchCard(1)}>Thẻ tiếp <Icon name="chevronRight" size={18} /></button></div><div className="lw-rating-area"><p>{flipped ? "Bạn nhớ thẻ này ở mức nào?" : "Lật thẻ để tự đánh giá độ nhớ của bạn."}</p><div className="lw-ratings">{ratings.map(rating => <button type="button" key={rating.id} disabled={!flipped} className={`lw-rating lw-rating-${rating.id} ${reviews[card.id] === rating.id ? "selected" : ""}`} onClick={() => reviewCard(rating.id)}><Icon name={rating.icon} size={18} />{rating.label}{reviews[card.id] === rating.id && <Icon name="check" size={13} />}</button>)}</div><small>Đánh giá được lưu trong demo. Lịch ôn tự động sẽ có khi tích hợp module Learning.</small></div></> : <div className="empty-state">Bài học chưa có flashcard mẫu.</div>}</section>}

        {tab === "quiz" && <section className="panel lw-quiz" ref={quizContainer}><div className="lw-card-heading"><div><span className="eyebrow">KIỂM TRA ĐIỀU BẠN ĐÃ HIỂU</span><h2>Một bài quiz nhỏ</h2><p className="muted">{bundle.quiz.questions.length} câu trắc nghiệm · Mỗi câu một đáp án</p></div><span className="lw-soft-badge">Câu hỏi & chấm điểm mẫu</span></div>{quizResult ? <><div className="lw-quiz-result" role="status"><div className="lw-score-ring" style={{ "--score": `${quizResult.scorePercentage}%` } as CSSProperties}><div><strong>{Math.round(quizResult.scorePercentage)}<small>%</small></strong><span>điểm quiz</span></div></div><div><span className="eyebrow">ĐÃ HOÀN THÀNH</span><h3>{quizResult.scorePercentage >= 75 ? "Bạn đang làm rất tốt." : "Mỗi lần thử, hiểu thêm một chút."}</h3><p>Bạn trả lời đúng <strong>{quizResult.correctAnswers}/{quizResult.totalQuestions} câu</strong>. Kết quả mẫu đã được lưu vào tiến độ.</p><button type="button" className="btn btn-primary" onClick={() => { setAnswers({}); setQuizResult(null); setQuizError(""); }}><Icon name="refresh" size={16} /> Làm lại bài quiz</button></div></div><h3 className="lw-result-heading">Cùng xem lại từng câu</h3><div className="lw-result-list">{quizResult.details.map((detail, index) => <article key={detail.questionId} className={`lw-result-item ${detail.isCorrect ? "correct" : "incorrect"}`}><div className="lw-result-title"><span className="lw-result-indicator"><Icon name={detail.isCorrect ? "check" : "close"} size={16} /></span><h4>{index + 1}. {bundle.quiz.questions.find(item => item.id === detail.questionId)?.question ?? "Câu hỏi"}</h4><span>{detail.isCorrect ? "Chính xác" : "Cần ôn lại"}</span></div><p><span>Bạn chọn:</span> {detail.selected}</p>{!detail.isCorrect && <p><span>Đáp án đúng:</span> {detail.correct}</p>}<div className="lw-explanation"><Icon name="sparkles" size={16} /><p>{detail.explanation}</p></div></article>)}</div></> : <><div className="lw-quiz-progress"><span>Đã trả lời <strong>{answeredCount}/{bundle.quiz.questions.length}</strong> câu</span><div><span style={{ width: `${bundle.quiz.questions.length ? answeredCount / bundle.quiz.questions.length * 100 : 0}%` }} /></div></div><div className="lw-question-list">{bundle.quiz.questions.map((item, index) => <fieldset className="lw-question" key={item.id} data-question={item.id} disabled={quizPending}><legend><span>CÂU {String(index + 1).padStart(2, "0")}</span>{item.question}</legend><div className="lw-answer-options">{item.options.map((option, optionIndex) => <label key={option} className={`lw-answer-option ${answers[item.id] === option ? "selected" : ""}`}><input type="radio" name={`quiz-${item.id}`} value={option} checked={answers[item.id] === option} onChange={() => { setAnswers(current => ({ ...current, [item.id]: option })); setQuizError(""); }} /><span className="lw-answer-letter">{String.fromCharCode(65 + optionIndex)}</span><span>{option}</span><span className="lw-answer-check"><Icon name="check" size={15} /></span></label>)}</div></fieldset>)}</div>{quizError && <p className="lw-error" role="alert">{quizError}</p>}<div className="lw-quiz-submit"><p>Hãy chọn đủ đáp án.<br /><span>Không sao nếu bạn chưa chắc chắn.</span></p><button type="button" className="btn btn-primary" disabled={quizPending || !bundle.quiz.questions.length} onClick={() => void submitQuiz()}>{quizPending ? <span className="spinner" /> : <Icon name="check" size={17} />}{quizPending ? "Đang chấm bài mẫu…" : "Nộp bài và xem kết quả"}</button></div></>}</section>}

        {tab === "documents" && <section className="panel lw-documents"><div className="lw-card-heading"><div><span className="eyebrow">NƠI KIẾN THỨC BẮT ĐẦU</span><h2>Tài liệu bài học</h2><p className="muted">{lesson.documents.length} tài liệu · Xem thông tin tệp, ghi chú và nội dung mẫu</p></div><button type="button" className="btn btn-secondary" onClick={onUpload}><Icon name="upload" size={17} /> Thêm tài liệu</button></div><div className="lw-document-notice"><Icon name="file" size={18} /><p>Trong bản demo, tệp bạn chọn chỉ được lưu tên và thông tin; ghi chú bạn nhập được lưu nguyên văn. Bản trích xuất có sẵn chỉ thuộc tài liệu mẫu. Demo chưa có OCR hoặc chuyển âm thanh thành văn bản.</p></div>{lesson.documents.length ? <div className="lw-document-grid"><div className="lw-document-list" aria-label="Danh sách tài liệu">{lesson.documents.map(document => <button type="button" key={document.id} className={`lw-document-item ${selectedDocument?.id === document.id ? "selected" : ""}`} aria-pressed={selectedDocument?.id === document.id} onClick={() => setSelectedDocumentId(document.id)}><span className="lw-file-icon"><Icon name="file" size={23} /></span><span className="lw-document-info"><strong>{document.name}</strong><small>{formatSize(document.size)} · {isSavedNote(document) ? "Ghi chú đã lưu" : document.transcript && document.sourceMode === "demo" ? "Tài liệu mẫu" : "Thông tin tệp"}</small><span className={`lw-status lw-status-${document.status}`}><span />{statusLabels[document.status]}</span></span><Icon name="chevronRight" size={16} /></button>)}</div><div className="lw-document-preview">{selectedDocument && <><div className="lw-preview-heading"><span className="eyebrow">NỘI DUNG XEM TRƯỚC</span><h3>{selectedDocument.name}</h3><span className="lw-soft-badge">{isSavedNote(selectedDocument) ? "Nội dung ghi chú" : selectedDocument.transcript && selectedDocument.sourceMode === "demo" ? "Bản trích xuất mẫu" : "Chưa phân tích tệp"}</span></div>{selectedDocument.transcript && selectedDocument.sourceMode === "demo" ? <div className="lw-transcript">{selectedDocument.transcript}</div> : <div className="lw-preview-empty"><div className="lw-icon-square"><Icon name="file" size={26} /></div><h3>Thông tin tệp đã được lưu</h3><p>Demo chưa đọc nội dung tài liệu này. Khi nối File Processing, bản trích xuất và trạng thái xử lý sẽ hiển thị tại đây.</p><dl><div><dt>Định dạng</dt><dd>{selectedDocument.mediaType || "Chưa xác định"}</dd></div><div><dt>Kích thước</dt><dd>{formatSize(selectedDocument.size)}</dd></div></dl></div>}</>}</div></div> : <div className="empty-state lw-doc-empty"><Icon name="file" size={36} /><h3>Thêm tài liệu đầu tiên của bạn</h3><p>Tập hợp ghi chú, PDF, hình ảnh hoặc bài giảng vào cùng một nơi.</p><button type="button" className="btn btn-primary" onClick={onUpload}><Icon name="plus" size={17} /> Chọn tài liệu</button></div>}</section>}
      </div>
    </div>
  );
}
