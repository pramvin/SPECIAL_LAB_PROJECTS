import { WalletView } from "@/components/wallet/WalletView";
import { getWalletData } from "@/lib/wallet";

export default async function WalletPage() {
  const data = await getWalletData();
  return <WalletView initial={data} />;
}
