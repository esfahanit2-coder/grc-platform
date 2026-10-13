import type { ReactNode } from "react";
import ProductWorkspace from "../../../components/product-workspace";

export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  return <ProductWorkspace>{children}</ProductWorkspace>;
}
