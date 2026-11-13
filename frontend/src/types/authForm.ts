export type Purpose = "consumer" | "producer";
export type Interest = "vegetables" | "fruits" | "seafood" | "experiences" | "short_term_jobs" | "farming";

// 画面入力値。API送信時には担当Bが最新の規約バージョンを加えて組み立てます。
export type SignupFormValues = {
  lastName: string;
  firstName: string;
  email: string;
  password: string;
  phone: string;
  birthDate: string;
  prefectureId: string;
  interests: Interest[];
  agreedToTerms: boolean;
  agreedToPrivacyPolicy: boolean;
};
export type SignupErrors = Partial<Record<keyof SignupFormValues, string>>;

export const initialSignupValues: SignupFormValues = {
  lastName: "", firstName: "", email: "", password: "", phone: "", birthDate: "",
  prefectureId: "", interests: [], agreedToTerms: false, agreedToPrivacyPolicy: false,
};

export const INTERESTS: { value: Interest; label: string }[] = [
  { value: "vegetables", label: "野菜" },
  { value: "fruits", label: "果物" },
  { value: "seafood", label: "魚介" },
  { value: "experiences", label: "体験" },
  { value: "short_term_jobs", label: "短期のお仕事" },
  { value: "farming", label: "就農" },
];
