export function profilePhoneField(phone: string): { phone?: string } {
  const normalized = phone.replace(/-/g, "").trim();
  return normalized ? { phone: normalized } : {};
}
