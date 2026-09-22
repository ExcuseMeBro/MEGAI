/**
 * Compatibility asset for installations created before compaction moved under the
 * active Laya extension. It intentionally registers nothing: `megai-laya/index.ts`
 * owns both the one runtime and `session_before_compact`.
 *
 * The installer migration may remove this asset once every managed installation
 * stages `megai-laya/compaction.ts` beside the active extension.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function retiredLayaCompaction(_pi: ExtensionAPI) {}
