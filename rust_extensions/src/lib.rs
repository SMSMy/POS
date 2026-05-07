//! مكتبة pos_calc - دوال حسابية سريعة لنظام نقاط البيع
//! Rust performance extensions for Atayb Cashier POS

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

/// حساب ملخص المبيعات من قائمة الفواتير
/// Calculate sales summary from list of invoices
#[pyfunction]
fn calculate_sales_summary(invoices: &Bound<'_, PyList>) -> PyResult<PyObject> {
    let py = invoices.py();

    let mut total_sales: f64 = 0.0;
    let mut total_tax: f64 = 0.0;
    let invoice_count = invoices.len();

    for item in invoices.iter() {
        let dict = item.downcast::<PyDict>()?;

        if let Some(total) = dict.get_item("total")? {
            total_sales += total.extract::<f64>()?;
        }

        if let Some(tax) = dict.get_item("tax_amount")? {
            total_tax += tax.extract::<f64>()?;
        }
    }

    let result = PyDict::new_bound(py);
    result.set_item("total_sales", total_sales)?;
    result.set_item("total_tax", total_tax)?;
    result.set_item("invoice_count", invoice_count)?;

    Ok(result.into())
}

/// حساب إجماليات السلة
/// Calculate cart totals (subtotal, tax, total)
#[pyfunction]
fn calculate_cart_totals(items: &Bound<'_, PyList>, tax_inclusive: bool) -> PyResult<PyObject> {
    let py = items.py();

    let mut subtotal: f64 = 0.0;
    let mut tax: f64 = 0.0;
    let mut total: f64 = 0.0;

    if tax_inclusive {
        for item in items.iter() {
            let dict = item.downcast::<PyDict>()?;

            let line_total: f64 = dict
                .get_item("line_total")?
                .map(|v| v.extract::<f64>())
                .transpose()?
                .unwrap_or(0.0);

            let tax_rate: f64 = dict
                .get_item("tax_rate")?
                .map(|v| v.extract::<f64>())
                .transpose()?
                .unwrap_or(0.0);

            let item_tax = line_total - (line_total / (1.0 + tax_rate));
            tax += item_tax;
            total += line_total;
        }
        subtotal = total - tax;
    } else {
        for item in items.iter() {
            let dict = item.downcast::<PyDict>()?;

            let line_total: f64 = dict
                .get_item("line_total")?
                .map(|v| v.extract::<f64>())
                .transpose()?
                .unwrap_or(0.0);

            let tax_rate: f64 = dict
                .get_item("tax_rate")?
                .map(|v| v.extract::<f64>())
                .transpose()?
                .unwrap_or(0.0);

            subtotal += line_total;
            tax += line_total * tax_rate;
        }
        total = subtotal + tax;
    }

    let result = PyDict::new_bound(py);
    result.set_item("subtotal", subtotal)?;
    result.set_item("tax", tax)?;
    result.set_item("total", total)?;

    Ok(result.into())
}

/// حساب خصم المكونات دفعة واحدة
/// Calculate ingredient deductions in batch
#[pyfunction]
fn calculate_ingredient_deductions(recipes: &Bound<'_, PyList>, quantity_sold: f64) -> PyResult<PyObject> {
    let py = recipes.py();
    let result = PyList::empty_bound(py);

    for item in recipes.iter() {
        let dict = item.downcast::<PyDict>()?;

        let ingredient_id: i64 = dict
            .get_item("ingredient_id")?
            .map(|v| v.extract::<i64>())
            .transpose()?
            .unwrap_or(0);

        let quantity_needed: f64 = dict
            .get_item("quantity_needed")?
            .map(|v| v.extract::<f64>())
            .transpose()?
            .unwrap_or(0.0);

        let deduct_amount = quantity_needed * quantity_sold;

        let entry = PyDict::new_bound(py);
        entry.set_item("ingredient_id", ingredient_id)?;
        entry.set_item("deduct_amount", deduct_amount)?;
        result.append(entry)?;
    }

    Ok(result.into())
}

/// حساب الهوامش الربحية دفعة واحدة
/// Calculate profit margins in batch
#[pyfunction]
fn batch_calculate_margins(products: &Bound<'_, PyList>) -> PyResult<PyObject> {
    let py = products.py();
    let result = PyList::empty_bound(py);

    for item in products.iter() {
        let dict = item.downcast::<PyDict>()?;

        let cost_price: f64 = dict
            .get_item("cost_price")?
            .map(|v| v.extract::<f64>())
            .transpose()?
            .unwrap_or(0.0);

        let selling_price: f64 = dict
            .get_item("selling_price")?
            .map(|v| v.extract::<f64>())
            .transpose()?
            .unwrap_or(0.0);

        let quantity: f64 = dict
            .get_item("quantity")?
            .map(|v| v.extract::<f64>())
            .transpose()?
            .unwrap_or(0.0);

        let margin_value = selling_price - cost_price;
        let margin_percent = if selling_price > 0.0 {
            (margin_value / selling_price) * 100.0
        } else {
            0.0
        };
        let total_value = selling_price * quantity;

        let entry = PyDict::new_bound(py);
        entry.set_item("margin_percent", margin_percent)?;
        entry.set_item("margin_value", margin_value)?;
        entry.set_item("total_value", total_value)?;
        result.append(entry)?;
    }

    Ok(result.into())
}

/// البحث السريع في المنتجات مع دعم العربية
/// Fast product search with Arabic support
///
/// Args:
///     query: نص البحث
///     products: قائمة المنتجات (كل منتج dict بـ id, name, barcode)
/// Returns:
///     قائمة المنتجات المطابقة
#[pyfunction]
fn search_products(query: &str, products: &Bound<'_, PyList>) -> PyResult<PyObject> {
    let py = products.py();
    let result = PyList::empty_bound(py);

    // تحويل البحث للحروف الصغيرة للمقارنة
    let query_lower = query.to_lowercase();
    let query_normalized = normalize_arabic(&query_lower);

    for item in products.iter() {
        let dict = item.downcast::<PyDict>()?;

        // جلب اسم المنتج
        let name: String = dict
            .get_item("name")?
            .map(|v| v.extract::<String>())
            .transpose()?
            .unwrap_or_default();

        // جلب الباركود
        let barcode: String = dict
            .get_item("barcode")?
            .map(|v| v.extract::<String>())
            .transpose()?
            .unwrap_or_default();

        // تطبيع النص العربي ومقارنة
        let name_normalized = normalize_arabic(&name.to_lowercase());
        let barcode_lower = barcode.to_lowercase();

        // البحث في الاسم أو الباركود
        if name_normalized.contains(&query_normalized) || barcode_lower.contains(&query_lower) {
            result.append(dict)?;
        }
    }

    Ok(result.into())
}

/// تطبيع النص العربي (إزالة التشكيل وتوحيد الأحرف)
fn normalize_arabic(text: &str) -> String {
    text.chars()
        .filter(|c| !is_arabic_diacritic(*c))
        .map(|c| normalize_arabic_char(c))
        .collect()
}

/// التحقق من علامات التشكيل العربية
fn is_arabic_diacritic(c: char) -> bool {
    matches!(c, '\u{064B}'..='\u{065F}' | '\u{0670}')
}

/// توحيد الأحرف العربية (مثل أ إ آ → ا)
fn normalize_arabic_char(c: char) -> char {
    match c {
        'أ' | 'إ' | 'آ' | 'ٱ' => 'ا',
        'ة' => 'ه',
        'ى' => 'ي',
        _ => c
    }
}

/// حساب إحصائيات المبيعات
/// Calculate sales statistics
///
/// Args:
///     invoices: قائمة الفواتير (كل فاتورة dict)
/// Returns:
///     إحصائيات شاملة
#[pyfunction]
fn calculate_statistics(invoices: &Bound<'_, PyList>) -> PyResult<PyObject> {
    let py = invoices.py();

    let count = invoices.len();
    if count == 0 {
        let result = PyDict::new_bound(py);
        result.set_item("count", 0)?;
        result.set_item("total_sales", 0.0)?;
        result.set_item("total_tax", 0.0)?;
        result.set_item("average_sale", 0.0)?;
        result.set_item("min_sale", 0.0)?;
        result.set_item("max_sale", 0.0)?;
        result.set_item("total_profit", 0.0)?;
        return Ok(result.into());
    }

    let mut total_sales: f64 = 0.0;
    let mut total_tax: f64 = 0.0;
    let mut total_cost: f64 = 0.0;
    let mut min_sale: f64 = f64::MAX;
    let mut max_sale: f64 = f64::MIN;

    for item in invoices.iter() {
        let dict = item.downcast::<PyDict>()?;

        let sale_total: f64 = dict
            .get_item("total")?
            .map(|v| v.extract::<f64>())
            .transpose()?
            .unwrap_or(0.0);

        let tax: f64 = dict
            .get_item("tax_amount")?
            .map(|v| v.extract::<f64>())
            .transpose()?
            .unwrap_or(0.0);

        let cost: f64 = dict
            .get_item("total_cost")?
            .map(|v| v.extract::<f64>())
            .transpose()?
            .unwrap_or(0.0);

        total_sales += sale_total;
        total_tax += tax;
        total_cost += cost;

        if sale_total < min_sale {
            min_sale = sale_total;
        }
        if sale_total > max_sale {
            max_sale = sale_total;
        }
    }

    let average_sale = total_sales / count as f64;
    let total_profit = total_sales - total_tax - total_cost;

    let result = PyDict::new_bound(py);
    result.set_item("count", count)?;
    result.set_item("total_sales", total_sales)?;
    result.set_item("total_tax", total_tax)?;
    result.set_item("average_sale", average_sale)?;
    result.set_item("min_sale", if min_sale == f64::MAX { 0.0 } else { min_sale })?;
    result.set_item("max_sale", if max_sale == f64::MIN { 0.0 } else { max_sale })?;
    result.set_item("total_profit", total_profit)?;

    Ok(result.into())
}

/// تحليل المخزون
/// Analyze inventory status
///
/// Args:
///     products: قائمة المنتجات
/// Returns:
///     تحليل شامل للمخزون
#[pyfunction]
fn analyze_inventory(products: &Bound<'_, PyList>) -> PyResult<PyObject> {
    let py = products.py();

    let total_products = products.len();
    let mut total_value: f64 = 0.0;
    let mut total_cost_value: f64 = 0.0;
    let mut low_stock_count: usize = 0;
    let mut out_of_stock_count: usize = 0;
    let mut active_count: usize = 0;

    let low_stock_items = PyList::empty_bound(py);
    let out_of_stock_items = PyList::empty_bound(py);

    for item in products.iter() {
        let dict = item.downcast::<PyDict>()?;

        let quantity: f64 = dict
            .get_item("quantity")?
            .map(|v| v.extract::<f64>())
            .transpose()?
            .unwrap_or(0.0);

        let min_alert: f64 = dict
            .get_item("min_alert_level")?
            .map(|v| v.extract::<f64>())
            .transpose()?
            .unwrap_or(0.0);

        let selling_price: f64 = dict
            .get_item("selling_price")?
            .map(|v| v.extract::<f64>())
            .transpose()?
            .unwrap_or(0.0);

        let cost_price: f64 = dict
            .get_item("cost_price")?
            .map(|v| v.extract::<f64>())
            .transpose()?
            .unwrap_or(0.0);

        let is_active: bool = dict
            .get_item("is_active")?
            .map(|v| v.extract::<bool>().or_else(|_| v.extract::<i32>().map(|i| i != 0)))
            .transpose()?
            .unwrap_or(true);

        if is_active {
            active_count += 1;
        }

        // حساب القيم
        total_value += quantity * selling_price;
        total_cost_value += quantity * cost_price;

        // فحص المخزون
        if quantity <= 0.0 {
            out_of_stock_count += 1;
            out_of_stock_items.append(dict)?;
        } else if quantity <= min_alert {
            low_stock_count += 1;
            low_stock_items.append(dict)?;
        }
    }

    let potential_profit = total_value - total_cost_value;

    let result = PyDict::new_bound(py);
    result.set_item("total_products", total_products)?;
    result.set_item("active_products", active_count)?;
    result.set_item("total_value", total_value)?;
    result.set_item("total_cost_value", total_cost_value)?;
    result.set_item("potential_profit", potential_profit)?;
    result.set_item("low_stock_count", low_stock_count)?;
    result.set_item("out_of_stock_count", out_of_stock_count)?;
    result.set_item("low_stock_items", low_stock_items)?;
    result.set_item("out_of_stock_items", out_of_stock_items)?;

    Ok(result.into())
}

/// تسجيل الوحدة
#[pymodule]
fn pos_calc(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(calculate_sales_summary, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_cart_totals, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_ingredient_deductions, m)?)?;
    m.add_function(wrap_pyfunction!(batch_calculate_margins, m)?)?;
    m.add_function(wrap_pyfunction!(search_products, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_statistics, m)?)?;
    m.add_function(wrap_pyfunction!(analyze_inventory, m)?)?;
    Ok(())
}
