# Task

Remote items are being delivered before their confirmation arrives. Fix delivery
so remote items wait for both content and confirmation. Local items should still
deliver as soon as their content is ready, even when an unrelated confirmation
is missing or pending. Unknown delivery modes must remain blocked. Leave the
local tests passing.
