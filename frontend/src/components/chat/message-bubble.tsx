"use client";

import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Children } from "react";
import type { ReactNode } from "react";
import { BotAvatar } from "bot-avatars";
import { SourceList } from "./source-list";
import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/cn";

/** Dòng "đang suy nghĩ" nhấp nháy ẩn hiện, hiện trong lúc chờ câu trả lời */
function PendingLine() {
  return (
    <div className="thinking-fade py-0.5 text-[14px] text-muted">
      Đang tìm tài liệu và soạn câu trả lời…
    </div>
  );
}

/**
 * Mỗi từ được bọc trong một span để chữ hiện dần khi stream.
 * React tái dùng span theo vị trí, nên từ nào đã hiện thì animation đã chạy xong
 * và không chạy lại — chỉ từ mới mount mới mờ dần vào.
 */
function fadeWords(children: ReactNode): ReactNode {
  return Children.map(children, (child) => {
    if (typeof child !== "string") return child;
    return child.split(/(\s+)/).map((piece, index) =>
      piece.trim() ? (
        <span
          key={index}
          className="stream-word"
          style={{ animationDelay: `${(index % 8) * 26}ms` }}
        >
          {piece}
        </span>
      ) : (
        piece
      ),
    );
  });
}

type Props = {
  message: ChatMessage;
  streaming?: boolean;
  /** Avatar chỉ hiện ở câu trả lời mới nhất; các câu cũ giữ chỗ để thẳng hàng */
  showAvatar?: boolean;
};

export function MessageBubble({
  message,
  streaming = false,
  showAvatar = false,
}: Props) {
  const isUser = message.role === "user";
  if (isUser) {
    return (
      <article className="message-in flex justify-end">
        <div className="max-w-[85%] rounded-[14px] rounded-br-sm bg-surface-card px-4 py-2.5 text-[15px] leading-relaxed text-ink sm:max-w-[75%]">
          {message.content}
        </div>
      </article>
    );
  }

  return (
    <article className="message-in flex items-start gap-3">
      {/* Avatar tự động "làm việc" khi chưa có chữ nào, nghỉ khi đã trả lời xong */}
      {showAvatar ? (
        <BotAvatar
          type="flower"
          shading="fabric"
          state={message.pending ? "working" : "default"}
          size={30}
          className="mt-0.5 shrink-0"
        />
      ) : (
        <span className="mt-0.5 w-[30px] shrink-0" aria-hidden="true" />
      )}
      <div className="min-w-0 flex-1">
        {message.pending && !message.content ? (
          <PendingLine />
        ) : (
          <div className={cn("answer-md", message.error && "text-error")}>
            <Markdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ href, children }) => (
                  <a href={href} target="_blank" rel="noopener noreferrer">
                    {children}
                  </a>
                ),
                ...(streaming
                  ? {
                      p: ({ children }) => <p>{fadeWords(children)}</p>,
                      li: ({ children }) => <li>{fadeWords(children)}</li>,
                    }
                  : {}),
              }}
            >
              {message.content}
            </Markdown>
            {streaming && <span className="stream-caret" aria-hidden="true" />}
          </div>
        )}

        {message.sources && message.sources.length > 0 && (
          <SourceList sources={message.sources} />
        )}
      </div>
    </article>
  );
}
