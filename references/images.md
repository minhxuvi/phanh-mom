# Rà ảnh cùng bài

Lập danh sách đúng số ảnh nhận được, kể cả ảnh trùng; gắn mỗi nhận xét với tên/thứ tự và vị trí dễ tìm (góc trên trái, dòng thứ ba, QR dưới cùng). Xem từng ảnh gốc ở kích thước đủ đọc. Không nói đã xem ảnh chỉ vì thấy đường dẫn hoặc OCR.

Rà ba lớp:

1. **Thông tin nhìn thấy:** mặt người, trẻ nhỏ, tên, chữ ký, số hồ sơ/tài khoản/điện thoại, địa chỉ, mã vạch/QR, GPS hoặc địa điểm/biển số, màn hình phụ và thông báo. Rà cả dữ liệu người thứ ba ở nền. Không làm nhận dạng danh tính từ mặt.
2. **Ý nghĩa và quyền:** ảnh có chứng minh đúng phát biểu đi kèm không; có bị cắt mất ngày/điều kiện; quyền chụp khác quyền công bố; ai có quyền cho phép; có đang mô tả cáo buộc như sự thật bằng cách đặt ảnh cạnh chữ. Không kết luận giấy tờ thật, người phạm tội hoặc được phép đăng từ hình thức ảnh.
3. **File xuất:** metadata, tên file, thumbnail, lớp ẩn/ảnh nhiều trang có thể còn dữ liệu. Nếu chỉ có ảnh đã render trong chat, không biết EXIF file gốc — ghi chưa kiểm, không nói đã sạch.

OCR với `review.py ocr` trả chữ, confidence và hộp tọa độ. Đối chiếu trực tiếp tên, số, ngày với ảnh; confidence cao không xác minh nội dung. OCR trống/lỗi không chứng minh ảnh không có dữ liệu. Không có vision: nói “Đã rà chữ OCR; chưa rà mặt, nền, QR và bố cục ảnh”, yêu cầu người dùng kiểm các vùng ấy hoặc chuyển sang model có vision; vẫn hoàn thành phần chữ.

Nếu người dùng yêu cầu bản ảnh đã xử lý: giữ ảnh nguồn, tạo bản mới, che kín/cắt phần cần bỏ thay vì làm mờ yếu hoặc che nửa số; không dựng lại chứng cứ, không thay thông tin giấy tờ. Xuất ảnh phẳng, kiểm nhìn lại và OCR lại vùng che; kiểm metadata bằng công cụ có thật. Nếu thiếu công cụ, trả hướng dẫn xử lý, không báo đã sửa ảnh. Review ảnh không đòi hỏi tự cài thư viện hoặc gọi dịch vụ cloud.
