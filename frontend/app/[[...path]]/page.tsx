import { Suspense } from "react";
import StudyApp from "../../components/StudyApp";
export default function Page() {
  return <Suspense fallback={<div className="boot-screen"><span className="spinner"/>Đang mở không gian học tập…</div>}><StudyApp/></Suspense>;
}
