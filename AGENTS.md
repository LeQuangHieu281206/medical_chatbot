# Quy ước commit message

Áp dụng cho toàn bộ repo. Mục tiêu: đọc log là hiểu commit làm gì, phạm vi nào,
và có phải breaking change hay không. File này chỉ dùng local (đã gitignore).

## Quy trình commit

1. Soạn commit message theo quy ước bên dưới.
2. Hiển thị đầy đủ message (subject, body, footer) và danh sách file sẽ commit.
3. Chờ người dùng xác nhận rõ ràng. Nếu người dùng sửa message, hiển thị lại
   bản đã sửa và chờ xác nhận lần nữa.
4. Chỉ chạy `git commit` sau khi được xác nhận. Không tự commit, amend hay push
   khi chưa được yêu cầu.

## Định dạng

```
<type>(<scope>): <subject>

[body - vì sao thay đổi, không phải kể lại code]

[footer - breaking change, refs]
```

Ngôn ngữ: toàn bộ subject, body và footer viết tiếng Việt. Giữ nguyên tên kỹ
thuật (class, endpoint, biến môi trường) và các từ khóa `BREAKING CHANGE`,
`Refs`.

Dòng tiêu đề (subject) nên dưới 50 ký tự, tối đa **72 ký tự**, không kết thúc
bằng dấu chấm.

## type

| type       | Dùng khi                                                                 |
| ---------- | ------------------------------------------------------------------------ |
| `feat`     | Thêm chức năng mới cho người dùng                                        |
| `fix`      | Sửa lỗi đang hoạt động sai                                               |
| `refactor` | Đổi cấu trúc code, không đổi hành vi                                     |
| `perf`     | Cải thiện hiệu năng                                                      |
| `style`    | Chỉ format code, khoảng trắng, dấu chấm phẩy. Không đổi logic và không đổi giao diện người dùng nhìn thấy |
| `test`     | Thêm/sửa test                                                            |
| `docs`     | Tài liệu, README, comment                                                |
| `build`    | Maven, npm, Docker, dependency                                           |
| `ci`       | Pipeline, script CI                                                      |
| `chore`    | Việc lặt vặt không thuộc các nhóm trên                                   |
| `revert`   | Hoàn tác một commit trước                                                |

Thay đổi giao diện mà người dùng nhìn thấy (CSS, bố cục) không dùng `style`:
dùng `feat` nếu thêm hoặc đổi giao diện có chủ đích, `fix` nếu sửa giao diện bị
lỗi.

## scope

Tên service hoặc module bị ảnh hưởng, viết thường:

`payment-service`, `booking-service`, `auth-service`, `user-service`,
`movie-service`, `api-gateway`, `eureka-server`, `frontend`, `infra`.

Nhiều scope thì lấy scope chính, phần còn lại ghi trong body. Bỏ scope nếu
thay đổi thật sự chạm toàn repo.

Khi thêm service hoặc module mới, cập nhật danh sách scope ở trên trong cùng
commit hoặc commit ngay sau đó.

`infra` là scope chỉ nơi thay đổi (docker-compose, cấu hình triển khai dùng
chung). Type vẫn chọn theo bản chất thay đổi:

- Sửa Dockerfile, docker-compose, dependency: `build(infra)`
- Sửa pipeline, script CI: `ci(infra)`
- Việc vặt khác trong hạ tầng: `chore(infra)`

## Subject

- Viết tiếng Việt, mô tả **kết quả** thay đổi.
- Bắt đầu bằng động từ thường: `thêm`, `sửa`, `bỏ`, `đổi`, `tách`, `gộp`.
- Nêu đối tượng cụ thể. Không dùng câu chung chung như "sửa lỗi", "update code".

```
fix(payment-service): xác nhận thanh toán VNPay ngay tại return URL
feat(frontend): thêm bộ lọc suất chiếu theo rạp
refactor(booking-service): tách logic giữ ghế khỏi BookingService
```

Không đạt:

```
fix: sửa lỗi
update
Sửa các lỗi liên quan
```

## Body

- Cách một dòng trống so với subject. Ngắt dòng ở 72 ký tự.
- Giải thích **vì sao** và **ảnh hưởng gì**, không kể lại từng dòng code.
- Nêu rủi ro, migration, biến môi trường mới nếu có.

## Footer

```
BREAKING CHANGE: đổi response /api/v1/payments trả về mảng
Refs: #12
```

`BREAKING CHANGE:` bắt buộc khi API, schema, hoặc cấu hình cũ không còn chạy
được. Ghi rõ cần đổi gì.

## Revert

Subject giữ nguyên subject của commit bị hoàn tác, đặt trong dấu nháy. Body ghi
hash của commit bị hoàn tác và lý do.

```
revert(payment-service): hoàn tác "xác nhận thanh toán VNPay ngay tại return URL"

Hoàn tác commit a1b2c3d vì làm lệch trạng thái đơn khi VNPay gọi IPN trùng.
Sẽ làm lại sau khi có cơ chế chống xử lý lặp.
```

## Quy tắc nội dung

- Một commit = một thay đổi logic. Không gộp nhiều task không liên quan.
- Không commit file sinh tự động (`target/`, `.next/`, log, `.env`).
- Không commit secret. Cấu hình dùng biến môi trường, commit placeholder.
- Commit phải build được: chạy compile/test tối thiểu trước khi commit.
