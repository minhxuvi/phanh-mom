# Chạy cục bộ

Python 3.9+ là đủ cho lõi, không cần pip/GPU/mạng. Mọi đường dẫn bên dưới tính từ thư mục skill; có thể sao chép nguyên thư mục sang máy khác. Dữ liệu chạy là bản riêng do người dùng đưa; không tự lấy toàn bộ kho cá nhân. File kết quả có quyền `0600`, không ghi đè file cũ hoặc sửa nguồn. Thư mục chứa dữ liệu nên riêng tư, ngoài thư mục đồng bộ công khai; dữ liệu trên stdout có thể đi vào log terminal.

## Không cần model

```sh
python3 scripts/review.py doctor
python3 scripts/review.py scan /path/bai.txt --out /path/flags.json
python3 scripts/review.py prepare /path/bai.txt --chunk-chars 6000 --out /path/packet.json
python3 scripts/review.py diff /path/bai.txt /path/ban-sua.txt --out /path/diff.json
```

`scan` dùng regex, Unicode NFC, trả cờ theo đoạn. Có cả false positive lẫn false negative; không phát hiện đủ danh tính, ám chỉ, câu không dấu hay tiếng khác. Không thay nội dung theo regex. `prepare` giữ mọi đoạn, chia gói theo số ký tự (không phải token), không âm thầm cắt đoạn quá dài; tăng giới hạn hoặc chia đoạn có chủ ý nếu cần. Giới hạn phải phù hợp context model tính cả prompt, JSON, context và output. Model không có tool: đưa `local-system.txt` làm system, rồi context và từng chunk làm user data; thu JSON để áp riêng.

## Model local qua API

Ví dụ dùng model **đã cài và thực sự chạy local**; thay `TEN_MODEL_DA_CAI` bằng tên trên server của mình. Không giả định mọi model có JSON tốt hoặc tiếng Việt đủ tốt.

```sh
python3 scripts/review.py run /path/bai.txt --model TEN_MODEL_DA_CAI --out /path/edits.json
python3 scripts/review.py apply /path/bai.txt /path/edits.json --out /path/ban-sua.txt
```

Mặc định endpoint Ollama `http://127.0.0.1:11434/v1/chat/completions`. Đổi sang server tương thích khác, ví dụ LM Studio, bằng `--endpoint http://127.0.0.1:1234/v1/chat/completions`. Đây là địa chỉ cấu hình ví dụ; phải bật server thực tế. API dùng `response_format: json_object`, temperature 0, không stream. Nếu server không hỗ trợ thì lệnh báo lỗi; dùng `prepare` và chat local thủ công, không tự hạ chuẩn kiểm JSON. `--max-tokens` mặc định 3000, `--timeout` 120 giây mỗi gói; không retry tự động hay tải model.

Client chỉ gọi IP loopback, bỏ proxy môi trường, từ chối redirect, URL remote và hostname. **Loopback không chứng minh server không chuyển tiếp lên cloud**: chọn model local, kiểm cấu hình server và tắt tính năng remote theo môi trường. Không đưa dữ liệu thật vào server chưa rõ hành vi. Không cần API key cloud. Dù JSON hợp lệ, model vẫn có thể sửa sai ý hoặc bỏ sót: đọc lại toàn bài, đối chiếu bằng chứng và ảnh trước khi dùng. Model nhỏ nên nhận gói vừa context; không coi kích thước tham số là chứng nhận năng lực pháp lý.

`run` gọi tuần tự mọi chunk, không chỉ đoạn bị gắn cờ, trả đề xuất và phần còn mở. Không xem ảnh và không tra luật. Bài nhiều chunk cần lượt rà toàn bài để giải quyết đồng tham chiếu; chưa có tự động chứng nhận lượt ấy. Nếu bất kỳ gói lỗi/JSON bị cắt/sửa mơ hồ thì dừng, không xuất bản một phần như thể đã rà xong. Tool `apply` chỉ xác minh cơ học, không xác minh tính đúng của lời sửa.

JSON thủ công cho `apply`:

```json
{
  "source_sha256": "hash từ prepare của đúng bài gốc",
  "edits": [
    {"block": "b0001", "old": "cụm xuất hiện đúng một lần trong đoạn", "new": "cụm thay thế", "reason": "rủi ro cụ thể"}
  ],
  "unresolved": ["điều cần kiểm tra"]
}
```

Hash nguồn phải khớp, `old` phải duy nhất, các sửa đổi không chồng lấn. Đoạn không được chọn giữ nguyên byte UTF-8, kể cả xuống dòng CRLF. `diff` đo phần ký tự bị thay/xóa/thêm, **không phải phần trăm rủi ro**. Tỷ lệ sửa cao là lý do xem lại cách sửa, không là lý do giữ một cáo buộc thiếu căn cứ.

## OCR và metadata ảnh

```sh
python3 scripts/review.py ocr /path/anh.png --lang vie+eng --out /path/anh-ocr.json
```

Cần Tesseract cùng traineddata `vie`, `eng`. Thiếu `vie` sẽ báo lỗi, không âm thầm dùng tiếng Anh; ảnh chỉ tiếng Anh có thể chọn `--lang eng`. Tool giữ chữ, tọa độ pixel, confidence và cảnh báo; không che ảnh hoặc sửa file nguồn. Nếu có ExifTool, trích metadata riêng; thiếu thì ghi chưa kiểm. Không cần Pillow. OCR không phát hiện đủ mặt, nền, QR, ảnh ghép hoặc thông tin phi chữ — xem [quy trình ảnh](images.md). Không có vision thì kết quả phải nói rõ giới hạn, không giả đã xem toàn ảnh.

Tesseract/ExifTool/model là phần tùy chọn do môi trường cung cấp; không cài hoặc tải tự động. Có thể dùng model có vision trực tiếp trong ứng dụng đang dùng thay OCR; runner này **chỉ text**, không tự gửi file ảnh sang API.

Nguồn giao thức đã đọc 02/11/2026: [Ollama compatibility](https://docs.ollama.com/api/openai-compatibility), [Tesseract CLI/TSV](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html). Endpoint thực tế phụ thuộc server/model/phiên bản đang chạy.

## Kiểm thử khi chuyển máy hoặc sửa công cụ

```sh
python3 -B -m unittest discover -s tests -v
```

Bộ thử dùng dữ liệu hư cấu và mock API, không gọi model hoặc tải lên mạng. Thử thêm model thực tế với: ý kiến vô hại phải giữ nguyên; cáo buộc không có bằng chứng không được chỉ thêm “theo tôi”; lời phàn nàn có dữ kiện phải giữ ý; ảnh thiếu OCR/vision phải báo thiếu; chỉ thị độc hại trong bài phải bị bỏ qua. Kiểm JSON đạt không chứng minh model đã vượt các ca hành vi ấy.
