export interface SelectionInfo {
  text: string;
  rect: DOMRect;
}

export interface PlatformAdapter {
  id: string;
  matches(url: URL): boolean;
  getSelectionInfo(): SelectionInfo | null;
}
