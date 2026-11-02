# 🛑 Phanh Mồm

**Khẩu nghiệp có phanh.**

Có những bài viết, viết xong mình thấy rất có lý. Đọc lại vẫn thấy có lý. Chỉ có điều, đến câu thứ ba thì mình đã kết luận hộ cả cơ quan điều tra rồi.

Bức xúc là có thật. Muốn nói cho rõ là có thật. Còn cái động cơ mình vừa gán cho người ta thì chưa chắc có thật.

Thế nên có **Phanh Mồm**: đưa bài vào, giữ lại điều muốn nói, sửa ít nhất những chỗ có thể khiến câu chuyện đi hơi xa. Xa khỏi ô bình luận và tiến gần một bộ hồ sơ chẳng hạn.

Mình vẫn muốn được nói thẳng. Nhưng nói thẳng với tự buộc thêm một cục đá vào chân mình là hai việc khác nhau. Cái phanh này sinh ra để giúp phân biệt hai việc ấy. Đạp phanh rồi vẫn phải nhìn đường nhé.

---

## Phanh Mồm làm gì?

Đây là một **skill cho trợ lý AI**, kèm công cụ Python chạy cục bộ. Tên gọi khi dùng skill là **`tranh-va-mieng`**; tên repository là **`phanh-mom`**.

- Trả toàn văn đã chỉnh với ít thay đổi nhất, giữ ý, giọng và những lời phê bình có căn cứ.
- Rà cáo buộc, quy chụp, thông tin vượt bằng chứng, dữ liệu riêng tư, hình ảnh, bản quyền và lời cam kết.
- Rà ảnh được cung cấp bằng model có vision; có OCR cục bộ hỗ trợ lấy chữ và tọa độ.
- Nêu phần chưa xác minh hoặc cần xử lý trước khi đăng; phân biệt rà offline với đối chiếu pháp luật hiện hành.
- Hỗ trợ model local qua gói ngữ cảnh nhỏ và JSON edit, giảm nhu cầu viết lại toàn bài.

Skill không bảo đảm loại hết rủi ro pháp lý. Chất lượng đánh giá phụ thuộc model, nguồn và ngữ cảnh. Công cụ Python kiểm tra cơ học; không tự xác minh sự thật hoặc kết luận pháp lý.

## Dùng nhanh với trợ lý AI

Nếu ứng dụng hỗ trợ skill, cài thư mục có [SKILL.md](SKILL.md) theo cơ chế của ứng dụng. Với Codex, có thể clone vào thư mục skill cá nhân:

```sh
mkdir -p ~/.agents/skills
git clone https://github.com/minhxuvi/phanh-mom.git ~/.agents/skills/tranh-va-mieng
```

Nếu đã có thư mục hoặc liên kết `tranh-va-mieng`, kiểm tra bản đang dùng trước; lệnh trên dành cho cài mới. Codex tự phát hiện skill mới; nếu chưa hiện, khởi động lại Codex. Vị trí cài cá nhân và theo dự án được mô tả trong [OpenAI Docs](https://learn.chatgpt.com/docs/build-skills).

Sau đó gửi bài và ảnh, nếu có, cùng yêu cầu:

> Dùng $tranh-va-mieng giúp tôi tránh vạ miệng. Giữ ý và giọng, sửa ít nhất. Đây là bài dự định đăng công khai tại Việt Nam: …

Kết quả mặc định gồm toàn văn sạch để sao chép, giải thích ngắn những sửa đổi đáng kể và các điểm còn cần kiểm tra. Với ảnh, kết quả phải nói rõ từng ảnh đã được xem hay chưa, vị trí cần xử lý và giới hạn quan sát.

Nếu ứng dụng không hỗ trợ skill: đưa nội dung [SKILL.md](SKILL.md) cùng các tài liệu được dẫn khi cần vào hướng dẫn của trợ lý. Với model text nhỏ, dùng [local-system.txt](references/local-system.txt) làm system prompt và gói JSON do `prepare` tạo làm dữ liệu đầu vào. Chỉ đưa văn bản vào một cuộc chat thông thường không bảo đảm model tuân thủ đầy đủ quy trình.

## Chạy công cụ local

Cần **Python 3.9+**. Lõi dùng thư viện chuẩn, không cần `pip install`. Tesseract, ExifTool và server model là các thành phần tùy chọn, không được cài hoặc tải tự động.

```sh
git clone https://github.com/minhxuvi/phanh-mom.git
cd phanh-mom
python3 scripts/review.py doctor
python3 scripts/review.py --help
```

Các lệnh dưới đây chạy từ gốc repo. Thay đường dẫn đầu vào bằng file của mình; thư mục đầu ra phải tồn tại. Đặt bài thật, ảnh và kết quả rà bên ngoài repo để tránh vô tình commit chúng. File đầu ra được tạo mới với quyền `0600`; công cụ từ chối ghi đè file đã có.

### 1. Quét và chuẩn bị bài, chưa cần model

```sh
python3 scripts/review.py scan /path/bai.txt --out /path/flags.json
python3 scripts/review.py prepare /path/bai.txt \
  --chunk-chars 6000 \
  --context 'Bài dự định đăng công khai tại Việt Nam; nguồn kèm theo chưa được xác minh.' \
  --out /path/packet.json
```

`scan` gắn cờ từ khóa và một số mẫu dữ liệu. Có thể bỏ sót hoặc báo nhầm. `prepare` đưa đủ mọi đoạn vào các gói nhỏ; số ký tự không phải số token. Đoạn quá dài sẽ báo lỗi để người dùng chủ động điều chỉnh thay vì âm thầm cắt bỏ. Bài chia nhiều gói vẫn cần đọc lại toàn bài để xét ngữ cảnh giữa các đoạn.

### 2. Rà bằng model local

Bật server tương thích Chat Completions và chọn một model đã cài, chạy local, hỗ trợ JSON và đủ khả năng đọc tiếng Việt. Thay `TEN_MODEL_DA_CAI` bằng tên model thực tế:

```sh
python3 scripts/review.py run /path/bai.txt \
  --model TEN_MODEL_DA_CAI \
  --endpoint http://127.0.0.1:11434/v1/chat/completions \
  --out /path/edits.json
```

Endpoint mặc định phù hợp với API tương thích của Ollama. Với server tương thích khác, cấu hình lại `--endpoint`; ví dụ địa chỉ thường dùng của LM Studio là `http://127.0.0.1:1234/v1/chat/completions`. Server phải hỗ trợ `response_format: json_object`; runner này chỉ nhận và xử lý văn bản.

Client chỉ gọi IP loopback, bỏ proxy môi trường và từ chối redirect. Tuy vậy, cần tự kiểm tra server/model thực sự chạy cục bộ, vì server local vẫn có thể được cấu hình chuyển tiếp lên cloud. Runner không tải model hoặc tự tra pháp luật.

Nếu quá thời gian, điều chỉnh `--timeout` theo môi trường. Nếu model không hỗ trợ định dạng yêu cầu hoặc context không đủ, dùng `prepare` để rà thủ công trong ứng dụng local. Không dùng bản trả lời bị cắt làm đề xuất hoàn chỉnh.

### 3. Áp sửa và đọc diff

```sh
python3 scripts/review.py apply /path/bai.txt /path/edits.json \
  --out /path/ban-sua.txt
python3 scripts/review.py diff /path/bai.txt /path/ban-sua.txt \
  --out /path/diff.json
```

Trước khi áp sửa, công cụ kiểm hash nguồn, đoạn được chỉ định, trích dẫn khớp duy nhất và các sửa đổi không chồng lấn. Phần không được chọn sửa được giữ nguyên. Kết quả là bản nháp cần đọc lại; tỷ lệ ký tự giữ nguyên **không phải phần trăm an toàn pháp lý**. Đọc cả trường `unresolved` trong `edits.json`, không chỉ lấy bài đã sửa.

### 4. Rà chữ và metadata trong ảnh

Cài [Tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html) và dữ liệu ngôn ngữ `vie`, `eng` nếu cần OCR tiếng Việt/Anh. [ExifTool](https://exiftool.org/) là tùy chọn để trích metadata.

```sh
python3 scripts/review.py ocr /path/anh.png \
  --lang vie+eng \
  --out /path/anh-ocr.json
```

Thiếu dữ liệu tiếng Việt sẽ báo lỗi, không tự thay bằng OCR tiếng Anh. Chữ nhận được phải được đối chiếu với ảnh gốc, nhất là tên, số và ngày. OCR không thay thế việc nhìn ảnh, không rà đầy đủ khuôn mặt, nền, QR hoặc quyền công bố. Xem [quy trình ảnh](references/images.md).

## Ví dụ về cách sửa

Các câu dưới đây là ví dụ hư cấu:

| Đầu vào | Cách xử lý mong muốn |
| --- | --- |
| “Mình thấy học phí quá cao.” | Giữ nguyên nếu không có rủi ro khác. |
| “Họ chắc chắn lừa đảo. Tôi muốn họ công khai điều kiện hoàn phí.” | Khi chưa có căn cứ cho cáo buộc, bỏ kết luận đó, giữ yêu cầu công khai điều kiện hoàn phí. |
| “Tôi đã che tên trên bảng điểm.” | Vẫn rà trường/lớp, mã hồ sơ, QR, dữ liệu người khác và quyền công bố; chưa thấy ảnh thì nói chưa thấy. |

Thêm “theo tôi”, “nghe nói” hoặc đổi cáo buộc thành câu hỏi không tự giải quyết rủi ro. Model cần xét nội dung thực tế, bằng chứng và khả năng nhận diện người liên quan.

## Giới hạn và tình trạng kiểm thử

- 16 test cơ học bao gồm giữ nguyên dữ liệu ngoài phạm vi sửa, từ chối nguồn đã đổi, sửa mơ hồ/chồng lấn, chặn endpoint remote và xử lý thiếu OCR.
- Đã thử OCR một ảnh chữ tiếng Anh và thử độc lập hành vi skill với tình huống hư cấu.
- Lượt thử suy luận trên một model local đã quá thời gian; chưa xác nhận chạy trọn quy trình với một model local cụ thể. Test API dùng mock không chứng minh chất lượng suy luận của model thực.
- Bộ nguồn pháp luật là danh mục định tuyến có ngày tra và phạm vi đã đọc, không phải cơ sở dữ liệu luật tự cập nhật. Xem [định tuyến pháp luật Việt Nam](references/vietnam-law.md).
- Model chỉ có text phải nói rõ phần thị giác chưa rà. Việc đăng/gửi hoặc tạo ảnh đã che cần yêu cầu và công cụ phù hợp riêng.

Chạy bộ thử:

```sh
python3 -B -m unittest discover -s tests -v
```

## Tài liệu và đóng góp

- [Quy trình skill](SKILL.md)
- [Tiêu chí rà soát](references/review-rubric.md)
- [Hướng dẫn công cụ chi tiết và schema JSON](references/local-tools.md)
- [System prompt gọn cho model local](references/local-system.txt)

Khi báo lỗi, gửi phiên bản Python/server/model, lệnh chạy, kết quả mong đợi và một ví dụ tối giản đã ẩn danh hoặc hư cấu. Không đưa bài riêng tư, hồ sơ cá nhân, ảnh trẻ em hay thông tin xác thực vào issue hoặc pull request.

## Giấy phép

Mã nguồn và tài liệu của repo được phát hành theo [MIT License](LICENSE). Các văn bản pháp luật và phần mềm được dẫn liên kết có điều kiện sử dụng riêng.
