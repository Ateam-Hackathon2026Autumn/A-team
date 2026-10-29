import { useNavigate } from 'react-router';

function InternalServerErrorPage() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-dvh items-center justify-center bg-[#f4f5f0] px-5 pb-10">
      <div className="w-full max-w-[440px] text-center">
        <p className="text-[15px] font-extrabold tracking-[0.06em] text-[#9a3220]">
          ERROR 500
        </p>
        <h1 className="mt-5 text-2xl font-bold text-[#26332b]">
          予期せぬエラーが発生しました
        </h1>
        <p className="mt-3 text-sm leading-[1.8] text-[#5b675f]">
          只今サーバーで問題が発生しています。
          <br />
          しばらく経ってから再度お試しください。
        </p>
        <button
          type="button"
          className="mt-8 rounded-full bg-[#2f6b4f] px-10 py-3.5 font-bold text-white"
          onClick={() => navigate('/')}
        >
          ホームへ戻る
        </button>
      </div>
    </div>
  );
}

export default InternalServerErrorPage;
